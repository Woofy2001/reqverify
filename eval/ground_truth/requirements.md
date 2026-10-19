# TechStore Functional Requirements Specification

Document Version: 1.0.0
Author: Quality Assurance Lead
Status: Approved for Evaluation
Scope: TechStore Web Application (E-Commerce Platform)

---

### REQ-01: User Login Form Authentication
Registered users shall be able to log in by providing their email and password. Upon submitting valid credentials, the system shall authenticate the user and redirect to the product catalog.

### REQ-02: Email Format Validation on Login
The login form shall validate that the email address contains a valid domain structure with a top-level domain. Submissions with invalid email formats such as missing domain extensions shall be rejected with an error message.

### REQ-03: Minimum Password Length Enforcement
The login form shall enforce a minimum password length of at least 6 characters. If a user enters a password shorter than 6 characters, the form shall prevent submission and display a validation error.

### REQ-04: Product Catalog Category Filtering
The product catalog page shall provide category filters that allow users to view only products belonging to the selected category. Selecting a category shall immediately filter the displayed product list to items in that category.

### REQ-05: Product Maximum Price Filtering
The product catalog shall allow filtering items by maximum price. Setting a price threshold shall display all products with price less than or equal to the selected maximum price threshold.

### REQ-06: Out of Stock Badge Display
Products with a inventory stock count of zero shall display an 'Out of stock' badge. The add-to-cart button for out of stock products shall be disabled.

### REQ-07: Adding Products to Shopping Cart
Clicking the add to cart button on an available product shall increment the cart item count and add the selected item to the cart.

### REQ-08: Cart Line Total Calculation
In the shopping cart, each item line total shall accurately reflect the product unit price multiplied by the selected quantity. Changing item quantity shall dynamically update the line total.

### REQ-09: Backend Connection Pool and Query Performance
The backend database connection pool shall maintain a maximum of 20 concurrent connections and execute all catalog queries within 15 milliseconds without exposing pool metrics to the user interface.

### REQ-10: Promotional Coupon Code Discount Application
Users shall be able to apply promotional coupon codes in the shopping cart. Applying a valid coupon code shall deduct the stated discount amount from the cart subtotal rather than increasing the total.

### REQ-11: Cart Shipping Fee Calculation
The cart summary shall include a standard shipping fee for orders. Free shipping shall be granted if subtotal exceeds 100 dollars, otherwise standard shipping fee of 10 dollars shall be added to the order total.

### REQ-12: Multi-Step Checkout Shipping Address Validation
In step 1 of the multi-step checkout wizard, the user must provide a non-empty shipping address and city. Attempting to proceed to step 2 with an empty shipping address shall be blocked with an explicit validation error.

### REQ-13: Order Grand Total Computation at Checkout
The checkout order summary shall calculate the final grand total as subtotal minus discounts plus shipping fee. The displayed grand total must include shipping charges whenever shipping fee is applicable.

### REQ-14: Order Confirmation and Cart State Clearing
Upon successful placement of an order, the system shall navigate to the confirmation view and completely clear all items from the shopping cart.

### REQ-15: Admin Dashboard Order Status Modification
Administrative users shall be able to view customer orders and update the status of any pending order to 'Shipped'. The updated status shall be persisted and immediately reflected in the orders table.

### REQ-16: User Session Logout
Authenticated users shall have access to a logout option that terminates the active session and redirects the browser back to the login page.
