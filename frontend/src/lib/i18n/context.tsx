"use client";

import { createContext, useContext } from "react";

import { ptBR, type Messages } from "./pt-BR";

// Defaults to pt-BR; the PT/EN switch (#13) only swaps the provider value.
export const MessagesContext = createContext<Messages>(ptBR);

export function useMessages(): Messages {
  return useContext(MessagesContext);
}
