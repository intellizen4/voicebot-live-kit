import asyncio
import logging
from livekit.agents import JobContext, JobRequest, WorkerOptions, cli
from livekit.agents.llm import ChatContext, ChatMessage, ChatRole
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import silero, openai, deepgram, elevenlabs
from livekit import rtc

# TODO
# On participant join fetch telephone number of the user.
async def entrypoint(ctx: JobContext):
    initial_ctx = ChatContext(
        messages=[
            ChatMessage(
                role=ChatRole.SYSTEM,
                text='''
                    You are a voice assistant for HPZ Pet Rover.
                    Respond to the user's question based on the context of our store, HPZ Pet Rover. 
                    Ensure your answer is clear, concise, and informative.
                    Initial Message can be like this:
                    'Hello, Welcome to HPZ Pet Rover! I can assist you with various inquiries. I can provide details about our products, help with order queries, or answer general questions regarding our store. How can I assist you today?'

                    Your interface with users will be voice. 
                    You should use short and concise responses, and avoid usage of unpronounceable punctuation.
                    HPZ™ Pet Rover Strollers are designed in California for the ultimate comfort and convenience for you and your pets, so you can spend more time together, rain or shine.
                    The world's best pet strollers and accessories, made with love from our family to yours since 2016!
                    
                    When the user asks for something related to 'order' ask only for their phone number and nothing else.
                    Detect the user's phone number from the conversation and store it in the json format. If the country code is present in the phone number then save it with the country code.
                    If the country code is not present then add the USA's country code +1 to the phone number and then save it. The json format should be like this:
                    {
                        "phone_number": USER'S PHONE NUMBER
                    }
                    In response if phone number is present.
                    Answer the question from the chat context, if necesary.
                    ''',
            )
        ]
    )

    assistant = VoiceAssistant(
        vad=silero.VAD(),
        stt=deepgram.STT(),
        llm=openai.LLM(),
        tts=openai.TTS(voice="alloy"),
        chat_ctx=initial_ctx,
    )
    assistant.start(ctx.room)

    await asyncio.sleep(1)
    # Acts as a loop
    # print("[ LOG ] The attirbute of assistant are ------", dir(assistant))
    await assistant.say("Hello, Welcome to HPZ Pet Rover! I can assist you with various inquiries. I can provide details about our products, help with order queries, or answer general questions regarding our store. How can I assist you today?", allow_interruptions=True)
    
    # Initialize RAG processor
    # rag_processor = RAGProcessor()
    
    
    # Example query processing using RAG for customer details
    # query = "Tell me about my last order."
    # response = await assistant.llm.rag_processor.retrieve_and_answer(query, phone="1234567890")
    # print(f"RAG response: {response}")

    # await assistant.say(response, allow_interruptions=True)

    # # Example query processing using RAG for product details
    # query_product = "Tell me about the latest product."
    # response_product = await assistant.llm.rag_processor.retrieve_and_answer(query_product)
    # print(f"RAG response: {response_product}")

async def request_fnc(req: JobRequest) -> None:
    logging.info("Received request %s", req)
    await req.accept(entrypoint)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(request_fnc))



'''7 Types Of Pet Strollers Made With Love:

                    1. HPZ™ Pet Rover Premium
                    - Large stroller holds up to 75 lbs
                    - Convertible pet compartment
                    - Pump-free rubber wheels
                    - Reversible handlebar

                    2. HPZ™ Pet Rover XL
                    - Extra-large stroller holds up to 75 lbs
                    - Convertible pet compartment
                    - Aluminum Gold Frame
                    - Expandable front end

                    3. HPZ™ Pet Rover Prime
                    - Medium stroller holds up to 50 lbs
                    - Detachable carrier
                    - Aluminum gold frame
                    - All pump-free rubber wheels

                    4. HPZ™ Pet Rover Lite
                    - Light-weight stroller holds up to 45 lbs
                    - Airline cabin compatible
                    - 1-hand quick fold/unfold
                    - Travel-friendly features

                    5. HPZ™ PET ROVER TITAN HD
                    - Super-sized stroller holds up to 100 lbs
                    - Integrated access ramp
                    - 6x all-terrain rubber wheels
                    - Multi-pet friendly SUV

                    6. HPZ™ PET ROVER RUN
                    - Performance jogging stroller
                    - Sports stroller holds up to 50 lbs
                    - 3x large air-filled rubber wheels
                    - Outdoor activities features
                    
                    7. HPZ™ BINGO(Just launched)
                    - Compact carrier/stroller combo holds up to 20 lbs
                    - Detachable luxury carrier bag
                    - Airline cabin approved
                    - Sea, air & land travel friendly
                    
                    Also selling ACCESSORIES. Essential Travel Accessories & Genuine Replacement Parts for HPZ Pet Rover Strollers.
                    '''