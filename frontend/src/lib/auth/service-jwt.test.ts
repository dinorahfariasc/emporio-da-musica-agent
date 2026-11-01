import { jwtVerify } from "jose";
import { describe, expect, it } from "vitest";

import { AUDIENCE, ISSUER, mintServiceJwt } from "./service-jwt";

const SECRET = "test-secret-at-least-32-bytes-long!!";

describe("mintServiceJwt", () => {
  it("includes sub, username, iss, aud and a 120s lifetime", async () => {
    const token = await mintServiceJwt("user-1", "demo", SECRET);
    const { payload } = await jwtVerify(token, new TextEncoder().encode(SECRET), {
      issuer: ISSUER,
      audience: AUDIENCE,
    });
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

  it("fails verification against the wrong issuer or audience", async () => {
    const token = await mintServiceJwt("user-1", "demo", SECRET);
    const key = new TextEncoder().encode(SECRET);
    await expect(jwtVerify(token, key, { issuer: "someone-else" })).rejects.toThrow();
    await expect(jwtVerify(token, key, { audience: "someone-else" })).rejects.toThrow();
  });

  it("refuses to mint with a secret shorter than 32 characters", async () => {
    await expect(mintServiceJwt("user-1", "demo", "short-secret")).rejects.toThrow(
      /at least 32 characters/,
    );
  });
});
