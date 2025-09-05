from tobys_terminal.shared.customer_utils import get_grouped_customers

customer_dict, labels = get_grouped_customers()

print("📦 Available company labels:")
for label in labels:
    print("-", label)

print("\n🧵 Company dict keys:")
print(customer_dict.keys())
