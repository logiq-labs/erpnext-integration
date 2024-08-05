# eShipz ERPNext Integration
A Shipping Integration for ERPNext with eShipz Platform
## Features
* Creation of Shipment by Selecting the Service: Easily create shipments by selecting the desired service from eShipz.
* Rule-Based Shipment Creation: Automate shipment creation based on predefined rules.
* Printing Shipping Labels: Generate and print shipping labels directly within the Shipment DocType.
* Parcel Dimensions Templates: Use predefined templates for parcel dimensions to streamline the shipment process.
* Shipment Tracking: Track your shipments within ERPNext.
* Shipment Status Update: Automatically update the shipment status within the Shipment DocType.
  
## Setup
### API Key Setup:
1. Obtain an API key from your eShipz account.
2. Navigate to eShipz Settings in ERPNext.
3. Enter the API Token from eShipz in the appropriate field.

### Rule-Based Shipment Setup:
1. Obtain necessary access from eShipz for rule-based shipment creation.
2. Enable Allocation in eShipz Settings within ERPNext.
   
### Shipment Creation
1. Create Sales Invoice: Generate a sales invoice for the order. If necessary, create an eWay bill.
2. Create Delivery Note: Generate a delivery note against the sales invoice.
3. Create Shipment: Navigate to the Delivery Note and initiate the shipment creation process.

4. Select Shipment Details: Choose the purpose of shipment, pickup type, and delivery type.

5. Add Parcel Information: Enter the number of parcels, pickup date, and a description of the content.

6. Create Shipment: Click on the 'Create Shipment' button and select the desired service from the available options.

7. Assign Items to Parcels: Select the items for each parcel and submit the shipment for creation.

8. Manage Shipment: Use the available buttons to download or print the shipping label, cancel the shipment, track the shipment, and update the shipment status.

### Rule-Based Shipment Creation
Enable Allocation: Ensure Allocation is enabled in eShipz Settings.
Follow Steps 1 to 5 from Shipment Creation: Follow the initial steps to create a shipment, as outlined above.

6. Create Rule-Based Shipment: Click on the 'Create Rule Based Shipment button. Select the items for each parcel and submit the shipment for creation.

7. Manage Shipment: Use the available buttons to download or print the shipping label, cancel the shipment, track the shipment, and update the shipment status.
