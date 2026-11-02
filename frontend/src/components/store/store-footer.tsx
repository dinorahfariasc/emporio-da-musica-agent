"use client";

import { Logo } from "@/components/ui/brand-mark";
import { useMessages } from "@/lib/i18n/context";
import { STORE_INFO } from "@/lib/store-info";

import { STORE_SECTIONS } from "./sections";
import { ContactLink, StoreAddress } from "./store-sections";

// Footer: brand, contact channels, section links, legal name and CNPJ. Extra bottom padding on
// mobile keeps the chat FAB from covering the last line.
export function StoreFooter() {
  const { app, store } = useMessages();
  const { contact, footer, nav } = store;
  return (
    <footer className="border-t border-border bg-subtle">
      <div className="mx-auto grid w-full max-w-[1040px] gap-8 pt-10 pr-[max(16px,env(safe-area-inset-right))] pb-6 pl-[max(16px,env(safe-area-inset-left))] md:grid-cols-[1.2fr_1fr_1fr] md:px-10">
        <div>
          <Logo name={app.storeName} subtitle={store.hero.title} />
        </div>
        <div>
          <h2 className="t-label-s mb-3">{footer.contactTitle}</h2>
          <StoreAddress />
          <dl className="t-body-s mt-3">
            <dt className="text-secondary-text">{contact.phoneLabel}</dt>
            <dd><ContactLink channel="phone" /></dd>
            <dt className="text-secondary-text">{contact.whatsappLabel}</dt>
            <dd><ContactLink channel="whatsapp" /></dd>
            <dt className="text-secondary-text">{contact.emailLabel}</dt>
            <dd><ContactLink channel="email" /></dd>
          </dl>
        </div>
        <nav aria-label={footer.sectionsTitle}>
          <h2 className="t-label-s mb-3">{footer.sectionsTitle}</h2>
          <ul className="grid grid-cols-2 gap-x-4 md:grid-cols-1">
            {STORE_SECTIONS.map((section) => (
              <li key={section.id}>
                <a
                  href={`#${section.id}`}
                  className="t-body-s inline-flex min-h-11 items-center text-primary-text underline-offset-3 hover:underline md:min-h-9"
                >
                  {nav[section.nav]}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <div className="mx-auto w-full max-w-[1040px] border-t border-border pt-5 pr-[max(16px,env(safe-area-inset-right))] pb-[max(104px,calc(88px+env(safe-area-inset-bottom)))] pl-[max(16px,env(safe-area-inset-left))] md:px-10 lg:pb-10">
        <p className="t-caption text-secondary-text">
          {footer.legalNameLabel}: {STORE_INFO.legalName} · {footer.cnpjLabel}: {STORE_INFO.cnpj}
        </p>
      </div>
    </footer>
  );
}
