import { DefaultChatTransport, type UIMessageChunk } from "ai";

import type { ChatMessage } from "@/lib/chat/types";

type SendOptions = Parameters<DefaultChatTransport<ChatMessage>["sendMessages"]>[0];

/**
 * The chat transport, plus a flag telling whether the last response stream sent its `finish`
 * chunk. ai@7 ends a stream that closes early as `ready` with no error, and `finishReason` is
 * optional in the contract, so `onFinish` alone cannot tell a dropped stream apart (R2).
 */
export class ChatTransport extends DefaultChatTransport<ChatMessage> {
  sawFinish = false;

  async sendMessages(options: SendOptions): Promise<ReadableStream<UIMessageChunk>> {
    this.sawFinish = false;
    const stream = await super.sendMessages(options);
    return stream.pipeThrough(
      new TransformStream<UIMessageChunk, UIMessageChunk>({
        transform: (chunk, controller) => {
          if (chunk.type === "finish") this.sawFinish = true;
          controller.enqueue(chunk);
        },
      }),
    );
  }
}
