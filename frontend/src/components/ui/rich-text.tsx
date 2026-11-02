import { Fragment, type ReactNode } from "react";

type RichTextProps = {
  template: string;
  values: Record<string, ReactNode>;
};

// Like `format` from @/lib/i18n, but lets catalog copy wrap a placeholder in markup (e.g. the
// bold countdown in "Aguarde {time} para…") without splitting the sentence into several keys.
export function RichText({ template, values }: RichTextProps) {
  const parts = template.split(/(\{\w+\})/g);
  return (
    <>
      {parts.map((part, index) => {
        const key = part.match(/^\{(\w+)\}$/)?.[1];
        return (
          <Fragment key={index}>
            {key !== undefined && Object.hasOwn(values, key) ? values[key] : part}
          </Fragment>
        );
      })}
    </>
  );
}
