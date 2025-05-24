import asyncio
from livekit import api

async def main():
    lkapi = api.LiveKitAPI()
    request = api.CreateSIPDispatchRuleRequest(
        rule = api.SIPDispatchRule(
        dispatch_rule_callee = api.SIPDispatchRuleCallee(
                room_prefix = 'number-',
                randomize = False,
            )
        )
    )
    dispatch = await lkapi.sip.create_sip_dispatch_rule(request)
    print("created dispatch", dispatch)
    await lkapi.aclose()

if __name__ == "__main__":
    asyncio.run(main())