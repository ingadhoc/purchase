from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_post(self, **kwargs):
        """Override to support force_subtype_id from context."""
        # If force_subtype_id comes from context, use it
        if self.env.context.get("force_subtype_id"):
            kwargs["subtype_id"] = self.env.ref(self.env.context["force_subtype_id"]).id
        return super().message_post(**kwargs)
