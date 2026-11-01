import { jwtVerify } from "jose";
import { describe, expect, it } from "vitest";

import { mintServiceJwt } from "./service-jwt";

const SECRET = "test-secret-at-least-32-bytes-long!!";

describe("mintServiceJwt", () => {
  it("includes sub, username and a 120s lifetime", async () => {
    const token = await mintServiceJwt("user-1", "demo", SECRET);
    const { payload } = await jwtVerify(token, new TextEncoder().encode(SECRET));
    expect(payload.sub).toBe("user-1");
    expect(payload.username).toBe("demo");
    expect((payload.exp ?? 0) - (payload.iat ?? 0)).toBe(120);
  });

  it("fails verification against a different secret", async () => {
    const token = await mintServiceJwt("user-1", "demo", SECRET);
    await expect(
      jwtVerify(token, new TextEncoder().encode("a-completely-different-secret!!")),
    ).rejects.toThrow();
  });
});
