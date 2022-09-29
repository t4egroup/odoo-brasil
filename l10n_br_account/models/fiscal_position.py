from odoo import api, fields, models
from .cst import CST_ICMS
from .cst import CSOSN_SIMPLES
from .cst import CST_IPI
from .cst import CST_PIS_COFINS


class AccountFiscalPositionTaxRule(models.Model):
    _name = "account.fiscal.position.tax.rule"
    _description = "Regras de Impostos"
    _order = "sequence"

    sequence = fields.Integer(string="Sequência")


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    edoc_policy = fields.Selection(
        [
            ("directly", "Emitir agora"),
            ("after_payment", "Emitir após pagamento"),
            ("manually", "Manualmente"),
        ],
        string="Nota Eletrônica",
        default="directly",
    )

    journal_id = fields.Many2one(
        "account.journal",
        string="Diário Contábil",
        help="Diário Contábil a ser utilizado na fatura.",
        copy=True,
    )
    account_id = fields.Many2one(
        "account.account",
        string="Conta Contábil",
        help="Conta Contábil a ser utilizada na fatura.",
        copy=True,
    )
    # fiscal_observation_ids = fields.Many2many(
    #     'l10n_br_eletronic_document.nfe.fiscal.observation', string=u"Mensagens Doc. Eletrônico",
    #     copy=True)
    note = fields.Text("Observações")

    apply_tax_ids = fields.Many2many("account.tax", string="Impostos a aplicar")
    csosn_icms = fields.Selection(CST_ICMS + CSOSN_SIMPLES, string="CSOSN ICMS")
    icms_aliquota_credito = fields.Float(string="% Crédito de ICMS")

    fiscal_type = fields.Selection(
        [("saida", "Saída"), ("entrada", "Entrada"), ("import", "Entrada Importação")],
        string="Tipo da posição",
        copy=True,
    )

    serie_nota_fiscal = fields.Char("Série da NFe")
    finalidade_emissao = fields.Selection(
        [("1", "Normal"), ("2", "Complementar"), ("3", "Ajuste"), ("4", "Devolução")],
        "Finalidade",
        help="Finalidade da emissão de NFe",
        default="1",
    )
    ind_final = fields.Selection(
        [("0", "Não"), ("1", "Sim")],
        "Consumidor final?",
        help="Indica operação com Consumidor final. Se não utilizado usa\
        a seguinte regra:\n 0 - Normal quando pessoa jurídica\n1 - Consumidor \
        Final quando for pessoa física",
    )
    ind_pres = fields.Selection(
        [
            ("0", "Não se aplica"),
            ("1", "Operação presencial"),
            ("2", "Operação não presencial, pela Internet"),
            ("3", "Operação não presencial, Teleatendimento"),
            ("4", "NFC-e em operação com entrega em domicílio"),
            ("5", "Operação presencial, fora do estabelecimento"),
            ("9", "Operação não presencial, outros"),
        ],
        "Tipo de operação",
        help="Indicador de presença do comprador no\n"
        "estabelecimento comercial no momento\n"
        "da operação.",
        default="0",
    )

    @api.model
    def _get_fpos_by_region(self,country_id=False, state_id=False, zipcode=False, vat_required=False, partner=False):
        if not partner:
            return super(AccountFiscalPosition, self)._get_fpos_by_region(
                country_id=country_id, state_id=state_id, zipcode=zipcode,vat_required=vat_required
            )

        if not country_id:
            return False

        ind_final = '1' if partner.company_type == 'person' else '0'

        base_domain = [
            ('auto_apply', '=', True),
            ('vat_required', '=', vat_required),
            ('company_id', 'in', [self.env.company.id, False]),
            ('ind_final', '=', ind_final)
        ]
        null_state_dom = state_domain = [('state_ids', '=', False)]
        null_zip_dom = zip_domain = [('zip_from', '=', False), ('zip_to', '=', False)]
        null_country_dom = [('country_id', '=', False), ('country_group_id', '=', False)]

        if zipcode:
            zip_domain = [('zip_from', '<=', zipcode), ('zip_to', '>=', zipcode)]

        if state_id:
            state_domain = [('state_ids', '=', state_id)]

        domain_country = base_domain + [('country_id', '=', country_id)]
        domain_group = base_domain + [('country_group_id.country_ids', '=', country_id)]

        # Build domain to search records with exact matching criteria
        fpos = self.search(domain_country + state_domain + zip_domain, limit=1)
        # return records that fit the most the criteria, and fallback on less specific fiscal positions if any can be found
        if not fpos and state_id:
            fpos = self.search(domain_country + null_state_dom + zip_domain, limit=1)
        if not fpos and zipcode:
            fpos = self.search(domain_country + state_domain + null_zip_dom, limit=1)
        if not fpos and state_id and zipcode:
            fpos = self.search(domain_country + null_state_dom + null_zip_dom, limit=1)

        # fallback: country group with no state/zip range
        if not fpos:
            fpos = self.search(domain_group + null_state_dom + null_zip_dom, limit=1)

        if not fpos:
            # Fallback on catchall (no country, no group)
            fpos = self.search(base_domain + null_country_dom, limit=1)
        return fpos

    @api.model
    def get_fiscal_position(self, partner_id, delivery_id=None):
        """
        :return: fiscal position found (recordset)
        :rtype: :class:`account.fiscal.position`
        """
        if not partner_id:
            return self.env['account.fiscal.position']

        # This can be easily overridden to apply more complex fiscal rules
        PartnerObj = self.env['res.partner']
        partner = PartnerObj.browse(partner_id)
        delivery = PartnerObj.browse(delivery_id)

        company = self.env.company
        eu_country_codes = set(self.env.ref('base.europe').country_ids.mapped('code'))
        intra_eu = vat_exclusion = False
        if company.vat and partner.vat:
            intra_eu = company.vat[:2] in eu_country_codes and partner.vat[:2] in eu_country_codes
            vat_exclusion = company.vat[:2] == partner.vat[:2]

        # If company and partner have the same vat prefix (and are both within the EU), use invoicing
        if not delivery or (intra_eu and vat_exclusion):
            delivery = partner

        # partner manually set fiscal position always win
        if delivery.property_account_position_id or partner.property_account_position_id:
            return delivery.property_account_position_id or partner.property_account_position_id

        # First search only matching VAT positions
        vat_required = bool(partner.vat)
        fp = self._get_fpos_by_region(delivery.country_id.id, delivery.state_id.id, delivery.zip, vat_required, partner)

        # Then if VAT required found no match, try positions that do not require it
        if not fp and vat_required:
            fp = self._get_fpos_by_region(delivery.country_id.id, delivery.state_id.id, delivery.zip, False, partner)

        return fp or self.env['account.fiscal.position']
