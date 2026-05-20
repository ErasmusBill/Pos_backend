import logging
import httpx
from typing import Optional

logger = logging.getLogger("pos_notifications")


class NotificationProviderEngine:
    """
    Handles downstream platform communications (SMS Gateways, Email, and internal Slack alerts).
    Fully async to preserve extreme endpoint execution speeds.
    """

    def __init__(self):
        # In a real environment, pull these from your src.config.settings file
        self.sms_api_url = "https://api.arkesel.com/v2/sms/send"
        self.sms_api_key = "YOUR_ARKESEL_OR_HUBTEL_KEY_GOES_HERE"
        self.slack_webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/ENDPOINT"

    async def send_sms_async(self, recipient_phone: str, message: str) -> bool:
        """
        Dispatches transactional retail notifications or low-stock warnings via SMS.
        """
        # Quick sanitization guard for Ghanaian format layouts
        if recipient_phone.startswith("0"):
            recipient_phone = "+233" + recipient_phone[1:]

        payload = {
            "sender": "POS_ALERT",
            "recipient": [recipient_phone],
            "message": message
        }
        headers = {"api-key": self.sms_api_key}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(self.sms_api_url, json=payload, headers=headers)
                if response.status_code == 200 or response.status_code == 201:
                    return True
                logger.error(f"SMS Gateway rejected dispatch: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to reach downstream SMS transit hub: {str(e)}")
            return False

    async def send_slack_alert_async(self, channel_message: str) -> bool:
        """
        Forwards administrative security violations or system health anomalies straight to back-office channels.
        """
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.post(self.slack_webhook_url, json={"text": channel_message})
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Slack notification channel drop occurred: {str(e)}")
            return False