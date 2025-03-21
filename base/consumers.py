import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import RecentActivity

class ActivityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("recent_activity", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("recent_activity", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        await self.channel_layer.group_send("recent_activity", {
            "type": "send_activity",
            "message": message
        })

    async def send_activity(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({"message": message}))
