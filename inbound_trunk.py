import asyncio

from livekit import api

async def main():
  livekit_api = api.LiveKitAPI()

  trunk = api.SIPInboundTrunkInfo(
    name = "Sei AI Twilio trunk",
    numbers=["+1234567890"],
    krisp_enabled = True,
  )

  request = api.CreateSIPInboundTrunkRequest(
    trunk = trunk
  )

  trunk = await livekit_api.sip.create_sip_inbound_trunk(request)

  await livekit_api.aclose()

asyncio.run(main())