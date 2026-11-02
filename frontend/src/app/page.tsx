import { StoreSections } from "@/components/store/store-sections";
import { StoreShell } from "@/components/store/store-shell";

// Public store home (spec 009). The chat is a widget on this page; it asks for sign-in itself.
export default function Home() {
  return (
    <StoreShell>
      <StoreSections />
    </StoreShell>
  );
}
