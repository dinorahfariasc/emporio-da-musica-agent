import { notFound } from "next/navigation";
import { Suspense } from "react";

import { Gallery } from "./gallery";

export const metadata = { robots: { index: false } };

// DEV-only screen gallery: every approved screen rendered from EXEMPLO data, for visual QA.
// Never reachable in a production build.
export default function GalleryPage() {
  if (process.env.NODE_ENV === "production") notFound();
  return (
    <Suspense>
      <Gallery />
    </Suspense>
  );
}
