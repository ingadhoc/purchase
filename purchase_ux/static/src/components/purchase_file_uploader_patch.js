/** @odoo-module **/

import { PurchaseFileUploader } from "@purchase/components/purchase_file_uploader/purchase_file_uploader";
import { patch } from "@web/core/utils/patch";

patch(PurchaseFileUploader.prototype, {
    setup() {
        super.setup(...arguments);
        this.skipUpload = false;
    },

    async onClick(ev) {
        // Verificar si se debe omitir el upload
        const skip_upload = await this.orm.call(
            "ir.config_parameter",
            "get_param",
            ["purchase_ux.skip_bill_file_upload"]
        );

        if (skip_upload === "True") {
            // Crear factura directamente sin subir archivo
            ev.preventDefault();
            ev.stopPropagation();

            const resModel = this.resModel;
            const ids = await this.getIds();
            const action = await this.orm.call(
                resModel,
                "action_create_invoice",
                [ids, false],
                { context: { ...this.env.searchModel.context } }
            );
            this.action.doAction(action);
            return false;
        }

        // Comportamiento normal - verificar validaciones
        return super.onClick ? super.onClick(ev) : undefined;
    },
});
