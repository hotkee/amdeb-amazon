# -*- coding: utf-8 -*-

import logging

from .base_transfomer import BaseTransformer
from ...models_access import OdooProductAccess
from ...shared.model_names import (
    PRODUCT_NAME_FIELD,
    PRODUCT_DESCRIPTION_SALE_FIELD,
    PRODUCT_AMAZON_DESCRIPTION_FIELD,
    PRODUCT_PRODUCT_BRAND_FIELD,
)

_logger = logging.getLogger(__name__)


class CreateTransformer(BaseTransformer):

    def _convert_description(self, sync_value):
        title = self._product[PRODUCT_NAME_FIELD]
        self._check_string(sync_value, 'Title', title)

        description = self._product[PRODUCT_AMAZON_DESCRIPTION_FIELD]
        if not description:
            description = self._product[PRODUCT_DESCRIPTION_SALE_FIELD]
        self._check_string(sync_value, 'Description', description)

        brand = self._product[PRODUCT_PRODUCT_BRAND_FIELD]
        self._add_string(sync_value, 'Brand', brand)

        bullet_points = OdooProductAccess.get_bullet_points(
            self._odoo_product)
        if bullet_points:
            sync_value['BulletPoint'] = bullet_points

    def _convert_variation(self, sync_value):
        has_color = False
        has_size = False
        attributes = OdooProductAccess.get_attributes(self._product)
        for attr in attributes:
            if attr[0] == 'Color':
                sync_value['Color'] = attr[1]
                has_color = True
            if attr[0] == 'Size':
                sync_value['Size'] = attr[1]
                has_size = True

        if has_color and has_size:
            sync_value['VariationTheme'] = 'SizeColor'
        elif has_color:
            sync_value['VariationTheme'] = 'Color'
        elif has_size:
            sync_value['VariationTheme'] = 'Size'
        else:
            _logger.warning("No variant attribute found in sync transform.")
            sync_value = None
        return sync_value

    # check the required field
    # create a pseudo-sku for multi-variant template
    def _convert_sync(self, sync_op):
        sync_value = super(CreateTransformer, self)._convert_sync(sync_op)

        self._convert_description(sync_value)

        # only three creation possibilities:
        # it is a non-partial variant
        # it is a template: multi-variant or not
        if OdooProductAccess.product_is_variant(self._product):
            # this is an independent variant
            if self._odoo_product.is_partial_variant(sync_op):
                _logger.warning("wrong sync creation for partial variant.")
                sync_value = None
            else:
                sync_value['Parentage'] = 'child'
                sync_value = self._convert_variation(sync_value)
        else:
            if not sync_value.get('Description', None):
                self._raise_exception('Description')

            if OdooProductAccess.has_multi_variants(self._product):
                sync_value['Parentage'] = 'parent'

        return sync_value