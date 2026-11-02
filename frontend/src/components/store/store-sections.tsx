"use client";

import { Mail, MapPin, MessageCircle, Phone } from "lucide-react";
import { createElement, type ReactNode } from "react";

import { BrandMark } from "@/components/ui/brand-mark";
import { Button } from "@/components/ui/button";
import { format } from "@/lib/i18n";
import { useMessages } from "@/lib/i18n/context";
import { STORE_INFO } from "@/lib/store-info";
import { cn } from "@/lib/utils";

import { sectionIcon, type StoreSectionId } from "./sections";
import { useOpenChat } from "./use-chat-widget";

// Store home sections. Copy comes from the catalog (manual v2.1, customer-facing parts only);
// no prices or percentages are computed here, they are catalog text.
export function StoreSections() {
  return (
    <>
      <Hero />
      <div className="mx-auto w-full max-w-[1040px] pr-[max(16px,env(safe-area-inset-right))] pl-[max(16px,env(safe-area-inset-left))] md:px-10">
        <About />
        <Hours />
        <Contact />
        <Payment />
        <Returns />
        <Shipping />
        <Promotions />
        <Warranty />
        <Privacy />
      </div>
    </>
  );
}

// Solid surface so text stays legible over the staff background; `store-card` adds the hover lift.
const card = "store-card rounded-lg border border-border bg-surface p-5 shadow-[var(--elevation-sm)]";

function Section({ id, title, children }: { id: StoreSectionId; title: string; children: ReactNode }) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-title`}
      className="scroll-mt-20 border-t border-border py-10 first:border-t-0 md:scroll-mt-48 md:py-14 xl:scroll-mt-36 xl:in-data-[chat=open]:scroll-mt-48"
    >
      <div className="mb-6 flex items-center gap-3">
        <span
          aria-hidden
          className="grid size-11 shrink-0 place-items-center rounded-md bg-brand-subtle text-on-brand-subtle"
        >
          {createElement(sectionIcon(id), { className: "size-5" })}
        </span>
        <h2 id={`${id}-title`} className="t-title-m md:t-title-l">
          {title}
        </h2>
      </div>
      {children}
    </section>
  );
}

function Bullets({ items, className }: { items: readonly string[]; className?: string }) {
  return (
    <ul className={cn("t-body-m flex list-disc flex-col gap-2 pl-5 marker:text-secondary-text", className)}>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function Hero() {
  const { store } = useMessages();
  const openChat = useOpenChat();
  return (
    <section id="inicio" aria-labelledby="inicio-title" className="scroll-mt-20 border-b border-border bg-subtle/40 md:scroll-mt-48 xl:scroll-mt-36 xl:in-data-[chat=open]:scroll-mt-48">
      <div className="mx-auto flex w-full max-w-[1040px] items-center gap-10 pt-10 pr-[max(16px,env(safe-area-inset-right))] pb-12 pl-[max(16px,env(safe-area-inset-left))] md:px-10 md:pt-16 md:pb-16">
        <div className="min-w-0 flex-1">
          <p className="t-label-s text-on-brand-subtle">{store.hero.eyebrow}</p>
          <h1 id="inicio-title" className="t-display mt-3 md:text-[44px] md:leading-[52px]">
            {store.hero.title}
          </h1>
          <p className="t-body-l mt-4 max-w-[560px] text-secondary-text">{store.hero.lead}</p>
          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <Button onClick={openChat}>
              <MessageCircle aria-hidden />
              {store.hero.chatCta}
            </Button>
            <a
              href="#horario"
              className="inline-flex h-12 items-center justify-center rounded-md border border-strong bg-canvas px-6 text-base leading-5 font-semibold text-primary-text no-underline transition-colors duration-150 hover:border-action hover:text-on-brand-subtle active:bg-subtle"
            >
              {store.hero.visitCta}
            </a>
          </div>
          <ul className="mt-8 flex flex-wrap gap-2">
            {store.hero.highlights.map((item) => (
              <li
                key={item}
                className="t-label-s rounded-full border border-border bg-canvas px-3.5 py-2 text-primary-text transition-colors duration-150 hover:border-action/60 hover:bg-brand-subtle hover:text-on-brand-subtle"
              >
                {item}
              </li>
            ))}
          </ul>
        </div>
        <BrandMark className="hidden size-40 rounded-2xl shadow-[var(--elevation-card)] md:grid" iconClassName="size-20" />
      </div>
    </section>
  );
}

function About() {
  const { store } = useMessages();
  const { about } = store;
  return (
    <Section id="quem-somos" title={about.title}>
      <div className="t-body-l flex max-w-[720px] flex-col gap-4 text-primary-text">
        {about.paragraphs.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div className={card}>
          <h3 className="t-label-m">{about.onlyInstrumentsTitle}</h3>
          <p className="t-body-m mt-2 text-secondary-text">{about.onlyInstruments}</p>
        </div>
        <div className={card}>
          <h3 className="t-label-m">{about.missionTitle}</h3>
          <p className="t-body-m mt-2 text-secondary-text">{about.mission}</p>
        </div>
      </div>
    </Section>
  );
}

function Hours() {
  const { store } = useMessages();
  const { hours } = store;
  return (
    <Section id="horario" title={hours.title}>
      <p className="t-body-l max-w-[720px] text-secondary-text">{hours.intro}</p>
      <div className={cn(card, "mt-6 max-w-[560px] p-0")}>
        <table className="w-full text-left">
          <thead className="sr-only">
            <tr>
              <th scope="col">{hours.dayLabel}</th>
              <th scope="col">{hours.timeLabel}</th>
            </tr>
          </thead>
          <tbody>
            {hours.rows.map((row, index) => (
              <tr key={row.day} className={cn(index > 0 && "border-t border-border")}>
                <th scope="row" className="t-body-m px-5 py-4 font-medium">
                  {row.day}
                </th>
                <td
                  className={cn(
                    "t-label-s px-5 py-4 text-right tabular-nums",
                    index === hours.rows.length - 1 && "text-secondary-text",
                  )}
                >
                  {row.time}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="t-body-s mt-4 max-w-[720px] text-secondary-text">{hours.note}</p>
    </Section>
  );
}

const contactLink =
  "inline-flex min-h-11 items-center break-words text-link underline underline-offset-3 transition-[text-decoration-thickness] duration-150 hover:decoration-2 active:opacity-80";

export function StoreAddress() {
  const { store } = useMessages();
  return (
    <address className="t-body-m not-italic">
      {STORE_INFO.address.street}
      <br />
      {STORE_INFO.address.city}
      <br />
      {format(store.contact.postalCode, { code: STORE_INFO.address.postalCode })}
    </address>
  );
}

type ContactChannel = "phone" | "whatsapp" | "email";

export function ContactLink({ channel }: { channel: ContactChannel }) {
  const info = STORE_INFO[channel];
  const external = channel === "whatsapp";
  return (
    <a
      className={contactLink}
      href={info.href}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
    >
      {channel === "email" ? <EmailText address={info.display} /> : info.display}
    </a>
  );
}

// Lets a narrow column wrap the address right after "@" instead of mid-word.
function EmailText({ address }: { address: string }) {
  const at = address.indexOf("@");
  if (at < 0) return address;
  return (
    <span>
      {address.slice(0, at + 1)}
      <wbr />
      {address.slice(at + 1)}
    </span>
  );
}

function Contact() {
  const { store } = useMessages();
  const { contact } = store;
  const items = [
    { icon: MapPin, label: contact.addressLabel, value: <StoreAddress /> },
    { icon: Phone, label: contact.phoneLabel, value: <ContactLink channel="phone" /> },
    { icon: MessageCircle, label: contact.whatsappLabel, value: <ContactLink channel="whatsapp" /> },
    { icon: Mail, label: contact.emailLabel, value: <ContactLink channel="email" /> },
  ];
  return (
    <Section id="contato" title={contact.title}>
      <ul className="grid gap-4 sm:grid-cols-2">
        {items.map(({ icon: Icon, label, value }) => (
          <li key={label} className={cn(card, "flex gap-4")}>
            <Icon aria-hidden className="store-card-icon mt-0.5 size-5 shrink-0 text-secondary-text" />
            <div className="min-w-0">
              <h3 className="t-label-s text-secondary-text">{label}</h3>
              <div className="mt-1">{value}</div>
            </div>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function Payment() {
  const { store } = useMessages();
  const { payment } = store;
  return (
    <Section id="pagamento" title={payment.title}>
      <p className="t-body-l max-w-[720px] text-secondary-text">{payment.intro}</p>
      <ul className="mt-6 grid gap-4 sm:grid-cols-2">
        {payment.methods.map((method) => (
          <li key={method.name} className={card}>
            <h3 className="t-label-m">{method.name}</h3>
            <p className="t-body-m mt-1">{method.terms}</p>
            <p className="t-body-s mt-1 text-secondary-text">{method.note}</p>
          </li>
        ))}
      </ul>
      <div className={cn(card, "mt-4")}>
        <h3 className="t-label-m mb-3">{payment.installmentsTitle}</h3>
        <Bullets items={payment.installments} />
      </div>
    </Section>
  );
}

function Returns() {
  const { store } = useMessages();
  const { returns } = store;
  return (
    <Section id="trocas" title={returns.title}>
      <p className="t-body-l max-w-[720px] text-secondary-text">{returns.intro}</p>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {returns.groups.map((group) => (
          <div key={group.title} className={card}>
            <h3 className="t-label-m mb-3">{group.title}</h3>
            <Bullets items={group.items} />
          </div>
        ))}
      </div>
    </Section>
  );
}

function Shipping() {
  const { store } = useMessages();
  const { shipping } = store;
  return (
    <Section id="frete" title={shipping.title}>
      <div className="grid gap-4">
        <div className={card}>
          <h3 className="t-label-m mb-3">{shipping.localTitle}</h3>
          <Bullets items={shipping.local} />
        </div>
        <div className={card}>
          <h3 className="t-label-m">{shipping.otherTitle}</h3>
          <p className="t-body-m mt-2 text-secondary-text">{shipping.otherIntro}</p>
          <ul className="mt-4 grid gap-3 md:grid-cols-3">
            {shipping.carriers.map((carrier) => (
              <li key={carrier.name} className="rounded-md bg-subtle p-4">
                <h4 className="t-label-s">{carrier.name}</h4>
                <dl className="t-body-s mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                  <dt className="text-secondary-text">{shipping.estimateLabel}</dt>
                  <dd>{carrier.estimate}</dd>
                  <dt className="text-secondary-text">{shipping.trackingLabel}</dt>
                  <dd>{carrier.tracking}</dd>
                  <dt className="text-secondary-text">{shipping.insuranceLabel}</dt>
                  <dd>{carrier.insurance}</dd>
                </dl>
              </li>
            ))}
          </ul>
          <Bullets items={shipping.notes} className="mt-5 text-secondary-text" />
        </div>
      </div>
    </Section>
  );
}

function Promotions() {
  const { store } = useMessages();
  const { promotions } = store;
  return (
    <Section id="promocoes" title={promotions.title}>
      <p className="t-body-l max-w-[720px] text-secondary-text">{promotions.intro}</p>
      <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {promotions.campaigns.map((campaign) => (
          <li key={campaign.name} className={card}>
            <span className="t-caption inline-flex rounded-full bg-brand-subtle px-2.5 py-1 text-on-brand-subtle">
              {campaign.when}
            </span>
            <h3 className="t-label-m mt-3">{campaign.name}</h3>
            <p className="t-body-m mt-1 text-secondary-text">{campaign.detail}</p>
          </li>
        ))}
      </ul>
      <div className={cn(card, "mt-4")}>
        <h3 className="t-label-m mb-3">{promotions.rulesTitle}</h3>
        <Bullets items={promotions.rules} />
      </div>
    </Section>
  );
}

function Warranty() {
  const { store } = useMessages();
  const { warranty } = store;
  return (
    <Section id="garantia" title={warranty.title}>
      <div className="grid gap-4 md:grid-cols-2">
        <div className={card}>
          <h3 className="t-label-m">{warranty.legalTitle}</h3>
          <p className="t-body-m mt-2 text-secondary-text">{warranty.legal}</p>
        </div>
        <div className={card}>
          <h3 className="t-label-m">{warranty.makerTitle}</h3>
          <p className="t-body-m mt-2 text-secondary-text">{warranty.maker}</p>
        </div>
      </div>
      <div className={cn(card, "mt-4")}>
        <h3 className="t-label-m mb-3">{warranty.excludedTitle}</h3>
        <Bullets items={warranty.excluded} />
      </div>
    </Section>
  );
}

function Privacy() {
  const { store } = useMessages();
  const { privacy } = store;
  return (
    <Section id="privacidade" title={privacy.title}>
      <div className={card}>
        <p className="t-body-m">{privacy.intro}</p>
        <Bullets items={privacy.uses} className="mt-3" />
        <p className="t-body-m mt-4">{privacy.sharing}</p>
        <p className="t-body-m mt-2">{privacy.deletion}</p>
      </div>
    </Section>
  );
}
