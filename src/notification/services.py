
import uuid
from src.notification.providers import NotificationProviderEngine

class POSNotificationService:
    def __init__(self):
        self.provider = NotificationProviderEngine()

    async def dispatch_customer_digital_receipt(self, phone: str, invoice_number: str, total_amount: float):
        """
        Dispatches a transactional receipt summary directly to a customer's phone line.
        """
        msg = f"Thank you for shopping with us! Your invoice {invoice_number} for GHS {total_amount:.2f} has been processed successfully."
        # Fire and forget locally
        await self.provider.send_sms_async(recipient_phone=phone, message=msg)

    async def trigger_low_stock_logistics_alert(self, product_name: str, days_remaining: float, current_stock: int):
        """
        Alerts warehouse controllers to dispatch purchase orders immediately.
        """
        msg = (
            f"⚠️ *INVENTORY RUNOUT ALERT* ⚠️\n"
            f"Product: *{product_name}*\n"
            f"Current Stock: {current_stock} units\n"
            f"Predicted Runway: *{days_remaining} days remaining* based on sales velocity patterns.\n"
            f"Action: Please initiate vendor restocking sequences immediately."
        )
        # Push to back-office monitoring logs
        await self.provider.send_slack_alert_async(channel_message=msg)

    async def report_security_variance(self, manager_name: str, cashier_name: str, invoice_num: str, reversed_value: float):
        """
        Flags high-risk database transactions like immediate manager order reversals.
        """
        msg = (
            f"🚨 *SECURITY TRANSACTION ALERT* 🚨\n"
            f"Manager `{manager_name}` authorized an active order override.\n"
            f"Cashier Register Target: `{cashier_name}`\n"
            f"Invoice Affected: {invoice_num}\n"
            f"Financial Value Reversal: GHS {reversed_value:.2f}"
        )
        await self.provider.send_slack_alert_async(channel_message=msg)