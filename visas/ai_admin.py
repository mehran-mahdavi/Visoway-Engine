"""
Admin integration: custom URL + JSON endpoint for "Fill with AI" on change forms.
"""

from __future__ import annotations

import logging
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from visas.services.ai_generator import OpenRouterError, generate_fields_for_instance

logger = logging.getLogger(__name__)


class FillWithAiAdminMixin:
    """
    Add POST /admin/.../<id>/generate-ai/ and inject `ai_generate_url` on change forms.

    Subclasses should set `change_form_template` to the shared AI change form template.
    """

    change_form_template = "admin/visas/ai_change_form.html"

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        custom = [
            path(
                "<path:object_id>/generate-ai/",
                self.admin_site.admin_view(self._generate_ai_dispatch),
                name="%s_%s_generate_ai" % info,
            ),
        ]
        return custom + super().get_urls()

    def _generate_ai_dispatch(self, request: HttpRequest, object_id: str):
        """Apply CSRF protection consistent with admin POST endpoints."""
        view = csrf_protect(require_POST(self.generate_ai_view))
        return view(request, object_id=object_id)

    def generate_ai_view(self, request: HttpRequest, object_id: str) -> JsonResponse:
        if not request.user.is_staff:
            return JsonResponse({"ok": False, "error": "Forbidden."}, status=403)
        if not self.has_change_permission(request):
            return JsonResponse({"ok": False, "error": "Forbidden."}, status=403)

        obj = self.get_object(request, object_id)
        if obj is None:
            return JsonResponse({"ok": False, "error": "Object not found."}, status=404)

        try:
            updates = generate_fields_for_instance(obj)
        except OpenRouterError as exc:
            logger.warning("AI generation failed: %s", exc)
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)
        except Exception:
            logger.exception("Unexpected error during AI generation")
            return JsonResponse(
                {"ok": False, "error": "Unexpected server error."},
                status=500,
            )

        if not updates:
            return JsonResponse(
                {"ok": False, "error": "Model returned no fields to update."},
                status=400,
            )

        for field, value in updates.items():
            setattr(obj, field, value)
        obj.save()

        logger.info(
            "AI fill applied for %s id=%s fields=%s by user=%s",
            self.model._meta.label,
            getattr(obj, "pk", None),
            list(updates.keys()),
            request.user.pk,
        )

        return JsonResponse(
            {
                "ok": True,
                "updated_fields": list(updates.keys()),
            }
        )

    def changeform_view(
        self, request: HttpRequest, object_id: str | None = None, form_url: str = "", extra_context: Any = None
    ) -> HttpResponse | TemplateResponse:
        ctx = {**(extra_context or {})}
        if object_id:
            try:
                ctx["ai_generate_url"] = reverse(
                    "admin:%s_%s_generate_ai"
                    % (self.model._meta.app_label, self.model._meta.model_name),
                    args=[object_id],
                )
            except Exception:
                logger.exception("Could not reverse AI URL for %s", object_id)
        return super().changeform_view(  # type: ignore[misc]
            request,
            object_id,
            form_url,
            ctx,
        )
