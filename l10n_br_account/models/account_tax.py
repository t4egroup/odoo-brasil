from odoo import fields, models
from odoo.addons.l10n_br_account.models.cst import (
    CST_PIS_COFINS,
    CST_IPI,
)


class AccountTax(models.Model):
    _inherit = "account.tax"

    domain = fields.Selection(
        [
            ("icms", "ICMS"),
            ("icmsst", "ICMS ST"),
            ("pis", "PIS"),
            ("cofins", "COFINS"),
            ("ipi", "IPI"),
            ("iss", "ISS"),
            ("ii", "II"),
            ("icms_inter", "Difal - Alíquota Inter"),
            ("icms_intra", "Difal - Alíquota Intra"),
            ("fcp", "FCP"),
            ("irpj", "IRPJ"),
            ("csll", "CSLL"),
            ("irrf", "IRRF"),
            ("inss", "INSS"),
            ("outros", "Outros"),
        ],
        string="Tipo",
    )

    ipi_cst = fields.Selection(CST_IPI, string="CST IPI", default="99")
    pis_cst = fields.Selection(CST_PIS_COFINS, string="CST Pis", default="99")
    cofins_cst = fields.Selection(CST_PIS_COFINS, string="CST COFINS", default="99")
