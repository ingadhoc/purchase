# Copyright 2026 ADHOC SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPurchaseOrderTypeLock(PurchaseTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        # El lock global arranca apagado para aislar el efecto del flag por tipo.
        cls.company.po_lock = "edit"
        cls.vendor = cls.env["res.partner"].create({"name": "Test Vendor"})
        cls.type_lock = cls.env["purchase.order.type"].create(
            {"name": "Locking Type", "set_locked_on_confirmation": True}
        )
        cls.type_no_lock = cls.env["purchase.order.type"].create(
            {"name": "Non-locking Type", "set_locked_on_confirmation": False}
        )

    def _create_po(self, order_type, price_unit=100.0):
        return self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_type": order_type.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product_1.id,
                            "product_qty": 1.0,
                            "price_unit": price_unit,
                        }
                    ),
                ],
            }
        )

    def test_01_lock_on_confirmation_type_flag(self):
        """AC2: tipo con flag ON + global OFF -> la orden queda bloqueada (state 'done')."""
        po = self._create_po(self.type_lock)
        po.button_confirm()
        self.assertEqual(po.state, "done", "La OC de un tipo con 'Lock on Confirmation' debe quedar bloqueada")

    def test_02_no_lock_without_flag(self):
        """AC3: tipo con flag OFF + global OFF -> la orden queda editable (state 'purchase')."""
        po = self._create_po(self.type_no_lock)
        po.button_confirm()
        self.assertEqual(po.state, "purchase", "Sin flag y sin lock global la OC debe quedar editable")

    def test_03_global_lock_dominates(self):
        """AC4: lock global ON -> bloquea siempre, sin importar el flag (apagado) del tipo."""
        self.company.po_lock = "lock"
        po = self._create_po(self.type_no_lock)
        po.button_confirm()
        self.assertEqual(po.state, "done", "Con el lock global prendido la OC debe quedar bloqueada igual")

    def test_04_double_validation_respected(self):
        """AC5: con doble validación el bloqueo se aplica al aprobar, no al confirmar."""
        self.company.write(
            {
                "po_double_validation": "two_step",
                "po_double_validation_amount": 100.0,
            }
        )
        # Monto por encima del umbral confirmado por un usuario sin permiso de aprobar.
        po = self._create_po(self.type_lock, price_unit=1000.0)
        po.with_user(self.res_users_purchase_user).button_confirm()
        self.assertEqual(po.state, "to approve", "Pendiente de aprobación no debe bloquearse todavía")
        # Aprobación final (usuario manager) -> recién ahora bloquea.
        po.button_approve()
        self.assertEqual(po.state, "done", "Tras la aprobación final la OC del tipo con flag debe bloquearse")

    def test_05_flag_hidden_setting_reflects_global(self):
        """Análogo a Ventas: el check por tipo se oculta cuando el global manda.

        La visibilidad la gobierna `lock_confirmed_po_setting`, que refleja el lock global de la
        compañía del tipo. Con el global apagado el check queda visible; al prenderlo, se oculta.
        """
        self.type_lock.company_id = self.company
        self.company.po_lock = "edit"
        self.assertFalse(
            self.type_lock.lock_confirmed_po_setting,
            "Con el lock global apagado el check por tipo debe seguir visible",
        )
        self.company.po_lock = "lock"
        self.type_lock.invalidate_recordset(["lock_confirmed_po_setting"])
        self.assertTrue(
            self.type_lock.lock_confirmed_po_setting,
            "Con el lock global prendido el check por tipo debe ocultarse (como en Ventas)",
        )
