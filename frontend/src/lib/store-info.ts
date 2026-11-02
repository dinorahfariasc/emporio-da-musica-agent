// Store facts from the policies manual v2.1 (cover and §1.2 company data). Not UI copy: the same
// in every locale. Phone (calls) and WhatsApp (messages) are separate channels; the WhatsApp
// number is the one in the manual's WhatsApp section. Links are built from digits only (+55).
export const STORE_INFO = {
  legalName: "Empório da Música Instrumentos Musicais Ltda.",
  cnpj: "12.345.678/0001-90",
  address: {
    street: "Rua 14 de Maio, 3200 — Centro",
    city: "Campo Grande – MS",
    postalCode: "79202-333",
  },
  phone: { display: "(67) 3341-4444", href: "tel:+556733414444" },
  whatsapp: { display: "(67) 3321-4500", href: "https://wa.me/556733214500" },
  // The cover spelling (no accent); the §1.2 table has an accented variant.
  email: { display: "contato@emporiodamusica.com.br", href: "mailto:contato@emporiodamusica.com.br" },
} as const;
