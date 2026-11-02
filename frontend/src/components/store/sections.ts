import { Clock, CreditCard, Home, Lock, MapPin, RotateCcw, ShieldCheck, Store, Tag, Truck } from "lucide-react";

// Store page anchors, in page order. Ids are Portuguese like the site copy (shareable URLs).
export const STORE_SECTIONS = [
  { id: "inicio", nav: "home", icon: Home },
  { id: "quem-somos", nav: "about", icon: Store },
  { id: "horario", nav: "hours", icon: Clock },
  { id: "contato", nav: "contact", icon: MapPin },
  { id: "pagamento", nav: "payment", icon: CreditCard },
  { id: "trocas", nav: "returns", icon: RotateCcw },
  { id: "frete", nav: "shipping", icon: Truck },
  { id: "promocoes", nav: "promotions", icon: Tag },
  { id: "garantia", nav: "warranty", icon: ShieldCheck },
  { id: "privacidade", nav: "privacy", icon: Lock },
] as const;

export type StoreSectionId = (typeof STORE_SECTIONS)[number]["id"];

export function sectionIcon(id: StoreSectionId) {
  return STORE_SECTIONS.find((section) => section.id === id)!.icon;
}
