from marshmallow import Schema, fields, validate


class CartAddItemSchema(Schema):
    product_id = fields.Int(required=True)
    quantity = fields.Int(
        required=True,
        validate=validate.Range(min=1, error="Количество должно быть не меньше 1."),
    )


class CartUpdateItemSchema(Schema):
    product_id = fields.Int(required=True)
    quantity = fields.Int(
        required=True,
        validate=validate.Range(min=0, error="Количество не может быть отрицательным."),
    )


class CartRemoveItemSchema(Schema):
    product_id = fields.Int(required=True)


class WishlistItemSchema(Schema):
    product_id = fields.Int(required=True)
