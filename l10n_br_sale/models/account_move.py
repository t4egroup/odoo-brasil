from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    modalidade_frete = fields.Selection(
        [
            ("0", "0 - Contratação do Frete por conta do Remetente (CIF)"),
            ("1", "1 - Contratação do Frete por conta do Destinatário (FOB)"),
            ("2", "2 - Contratação do Frete por conta de Terceiros"),
            ("3", "3 - Transporte Próprio por conta do Remetente"),
            ("4", "4 - Transporte Próprio por conta do Destinatário"),
            ("9", "9 - Sem Ocorrência de Transporte"),
        ],
        string="Modalidade do frete",
        default="9",
    )
    quantidade_volumes = fields.Integer("Qtde. Volumes")
    # peso_liquido = fields.Float(string=u"Peso Líquido")
    peso_bruto = fields.Float(string="Peso Bruto")

    @api.onchange("invoice_line_ids")
    def onchange_weight(self):
        for move in self:
            if move.invoice_line_ids:
                move.peso_bruto = sum(
                    [
                        line.product_id.weight * line.quantity
                        for line in move.invoice_line_ids
                    ]
                )
            else:
                move.peso_bruto = 0
