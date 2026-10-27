"""Read-only: pull Shopify orders with attribution journey. CLI: pull_orders.py [SINCE=2026-08-19] -> orders.json."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shop import gql, root
Q = """query($c:String,$q:String){ orders(first:100, after:$c, query:$q, sortKey:CREATED_AT){
 pageInfo{hasNextPage endCursor}
 nodes{ name createdAt test cancelledAt displayFinancialStatus
  currentTotalPriceSet{shopMoney{amount}} totalDiscountsSet{shopMoney{amount}}
  discountCodes sourceName customAttributes{key value}
  customer{ id numberOfOrders createdAt orders(first:1, sortKey:CREATED_AT){nodes{name}} }
  lineItems(first:10){nodes{ title variantTitle quantity sellingPlan{name} customAttributes{key value} }}
  customerJourneySummary{ daysToConversion momentsCount{count}
   firstVisit{ landingPage referrerUrl source sourceType utmParameters{source medium campaign content} }
   lastVisit{ landingPage referrerUrl source sourceType utmParameters{source medium campaign content} } }
 } } }"""

def pull(since):
    out, cur = [], None
    while True:
        o = gql(Q, {'c': cur, 'q': f'created_at:>={since}'})['orders']; out += o['nodes']
        if not o['pageInfo']['hasNextPage']: return out
        cur = o['pageInfo']['endCursor']

if __name__ == '__main__':
    out = pull(sys.argv[1] if len(sys.argv) > 1 else '2026-08-19')
    os.makedirs(os.path.join(root, '.context/data'), exist_ok=True)
    json.dump(out, open(os.path.join(root, '.context/data/orders.json'), 'w'), indent=1)
    print('orders', len(out))
