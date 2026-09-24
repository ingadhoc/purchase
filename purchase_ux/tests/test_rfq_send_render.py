import subprocess
from unittest.mock import patch

from odoo.addons.base.models import ir_actions_report
from odoo.tests import TransactionCase
from odoo.tools.pdf import PdfFileWriter


class TestRfqSendRender(TransactionCase):
    """Opening the send-by-email wizard renders the order report once.

    The composer recomputes its attachments on every onchange; with the PDF
    rendered and stored before the composer exists, those recomputes reuse it
    instead of calling wkhtmltopdf again.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Supplier", "email": "supplier@example.com"})
        cls.product = cls.env["product.product"].create({"name": "Thing", "standard_price": 5.0, "list_price": 10.0})
        cls.order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [(0, 0, {"product_id": cls.product.id, "product_qty": 1, "price_unit": 5.0})],
            }
        )

    def _fake_wkhtmltopdf(self, args):
        self.renders += 1
        writer = PdfFileWriter()
        writer.add_blank_page(width=100, height=100)
        with open(args[-1], "wb") as pdf_file:
            writer.write(pdf_file)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    def _open_composer(self, order):
        action = order.with_context(send_rfq=True, force_report_rendering=True).action_rfq_send()
        return self.env["mail.compose.message"].with_context(action["context"], force_report_rendering=True).create({})

    def test_one_render_per_opening(self):
        self.renders = 0
        with patch.object(ir_actions_report, "_run_wkhtmltopdf", side_effect=self._fake_wkhtmltopdf):
            composer = self._open_composer(self.order)
            self.assertEqual(self.renders, 1, "the click renders the report once")
            self.assertTrue(self.order.access_token, "the portal token exists before the PDF name is fixed")
            stored = self.env["ir.attachment"].search(
                [("res_model", "=", "purchase.order"), ("res_id", "=", self.order.id)]
            )
            self.assertEqual(len(stored), 1)
            self.assertTrue(composer.attachment_ids)
            # every further recompute of the composer (one per onchange in the
            # web client) reuses the stored PDF
            for _ in range(3):
                self.env["mail.compose.message"].with_context(**composer.env.context).create({})
            self.assertEqual(self.renders, 1, "the composer never renders again")

    def test_render_again_after_edit(self):
        self.renders = 0
        with patch.object(ir_actions_report, "_run_wkhtmltopdf", side_effect=self._fake_wkhtmltopdf):
            self._open_composer(self.order)
            # saving the form writes the order, which moves its write_date; the
            # whole test shares one transaction timestamp, so move it by hand
            self.order.write(
                {
                    "order_line": [(1, self.order.order_line.id, {"price_unit": 6.0})],
                    "write_date": "2030-01-01 10:00:00",
                }
            )
            self._open_composer(self.order)
            self.assertEqual(self.renders, 2, "an edited order is rendered fresh")
