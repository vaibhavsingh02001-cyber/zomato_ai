# Zomato Restaurant Dataset Preview

This document provides a preview of the raw restaurant records we extract and process from the Hugging Face dataset `ManikaSaini/zomato-restaurant-recommendation`.

| Restaurant Name (`name`) | Rating (`rate`) | Cuisines (`cuisines`) | Approx Cost for Two (`approx_cost(for two people)`) | Location (`location`) |
| :--- | :--- | :--- | :--- | :--- |
| **Trattoria Roma** | 4.3/5 | Italian, Pizza | 800 | Delhi |
| **Spicy Tadka** | 4.5/5 | North Indian, Mughlai | 500 | Delhi |
| **Corner Café** | 3.9/5 | Café, Italian | 300 | Bangalore |
| **Golden Dragon** | 4.6/5 | Chinese, Asian | 1200 | Bangalore |
| **The Bistro** | 4.1/5 | Continental, French | 1500 | Bangalore |
| **Chai Point** | 3.8/5 | Beverages, Fast Food | 200 | Delhi |
| **Taco Bell** | 3.7/5 | Mexican, Fast Food | 400 | Delhi |
| **Sagar Ratna** | 4.0/5 | South Indian, North Indian | 600 | Delhi |
| **Punjab Grill** | 4.4/5 | North Indian | 1800 | Bangalore |
| **Empire Restaurant** | 4.2/5 | North Indian, Biryani, Kebab | 550 | Bangalore |

## Schema Fields & Normalization Rules

*   **Restaurant Name (`name`)**: Trimmed of leading/trailing whitespace. Deduplicated by combination of `(name, location)` case-insensitively, retaining the highest-rated record.
*   **Rating (`rate`)**: String format like `4.3/5` is parsed to a float `4.3`. Records with unparseable ratings like `"NEW"` or `"-"` are filtered out.
*   **Cuisines (`cuisines`)**: Comma-separated strings are split, trimmed, lowercased, and deduplicated into a sorted list (e.g. `["italian", "pizza"]`).
*   **Approx Cost (`approx_cost(for two people)`)**: Numeric string is parsed to integer and mapped to budget tiers:
    *   **Low**: <= ₹400 for two
    *   **Medium**: ₹401 to ₹1000 for two
    *   **High**: > ₹1000 for two
*   **Location (`location`)**: Case-insensitive location strings are canonicalized (e.g., mapping `"bengaluru"` or `"bangalore north"` to `"bangalore"`).
