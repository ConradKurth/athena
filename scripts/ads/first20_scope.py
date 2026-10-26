"""Scope the FIRST20 code (Meta ads offer) to the 60 and 90 packs, or roll back to the whole product.

Usage: python3 first20_scope.py apply|rollback|show
Owner decision 2026-10-20 was 60/90 only; reversed 2026-10-23: FIRST20 stays 20% on all packs. Do not apply unless the owner asks.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shop import gql
NODE = 'gid://shopify/DiscountCodeNode/1520041984227'
PRODUCT = 'gid://shopify/Product/8772579197155'
V60, V90 = 'gid://shopify/ProductVariant/46988488638691', 'gid://shopify/ProductVariant/47021084377315'

def show():
    d = gql('''query($id:ID!){ codeDiscountNode(id:$id){ codeDiscount{ ... on DiscountCodeBasic{ title status
      customerGets{ value{ ... on DiscountPercentage{percentage} } items{ ... on DiscountProducts{
        products(first:5){nodes{title}} productVariants(first:5){nodes{title}} } } } } } } }''', {'id': NODE})
    print(json.dumps(d['codeDiscountNode']['codeDiscount'], indent=1))

UPDATE = '''mutation($id:ID!,$d:DiscountCodeBasicInput!){ discountCodeBasicUpdate(id:$id, basicCodeDiscount:$d){
  userErrors{ field message } } }'''
def items(products):
    return {'customerGets': {'value': {'percentage': 0.2}, 'items': {'products': products}}}

cmd = sys.argv[1] if len(sys.argv) > 1 else 'show'
if cmd == 'apply':
    # two steps: add the variants first so the code is never left with nothing to discount
    for step in ({'productVariantsToAdd': [V60, V90]}, {'productsToRemove': [PRODUCT]}):
        e = gql(UPDATE, {'id': NODE, 'd': items(step)})['discountCodeBasicUpdate']['userErrors']
        if e: raise SystemExit(f'userErrors: {e}')
elif cmd == 'rollback':
    for step in ({'productsToAdd': [PRODUCT]}, {'productVariantsToRemove': [V60, V90]}):
        e = gql(UPDATE, {'id': NODE, 'd': items(step)})['discountCodeBasicUpdate']['userErrors']
        if e: raise SystemExit(f'userErrors: {e}')
show()
