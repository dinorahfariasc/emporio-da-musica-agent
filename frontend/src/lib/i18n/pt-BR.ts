// pt-BR copy catalog. Its shape (`Messages`) is the contract an `en` catalog must satisfy (#13).
export const ptBR = {
  app: {
    storeName: "Empório da Música",
    assistantName: "Melody",
    tagline: "Assistente virtual",
    title: "Melody · Empório da Música",
    description: "Assistente virtual da Empório da Música",
  },
  emptyState: {
    greeting: "Oi! Eu sou a Melody. Como posso te ajudar hoje?",
    suggestionsLabel: "Sugestões",
    suggestions: [
      "Vocês têm violão até R$ 1.000?",
      "Quais promoções estão ativas?",
      "Como faço para trocar um produto?",
      "Quais as formas de pagamento?",
    ],
  },
  input: {
    label: "Mensagem para a Melody",
    placeholder: "Escreva sua mensagem…",
    send: "Enviar",
    stop: "Parar",
  },
  status: {
    typing: "Melody está digitando…",
  },
  messages: {
    logLabel: "Conversa com a Melody",
    you: "Você",
  },
  tools: {
    search_products: "Buscando no catálogo…",
    get_product: "Consultando o produto…",
    find_similar_products: "Procurando opções parecidas…",
    get_active_promotions: "Verificando promoções…",
    calculate_payment_options: "Calculando formas de pagamento…",
    get_order_status: "Consultando seu pedido…",
    search_policies: "Consultando as políticas da loja…",
    get_store_info: "Buscando informações da loja…",
    check_return_eligibility: "Verificando se dá para trocar ou devolver…",
    request_return: "Abrindo solicitação de devolução…",
    register_complaint: "Registrando sua reclamação…",
    handoff_to_human: "Chamando um atendente…",
    fallback: "Consultando…",
  },
  toolState: {
    done: "concluído",
    failed: "não foi possível concluir",
  },
  availability: {
    in_stock: "Em estoque",
    out_of_stock: "Esgotado",
    coming_soon: "Em breve",
    discontinued: "Fora de linha",
  },
  product: {
    discount: "-{percent}",
    originalPrice: "Preço original: {price}",
  },
  errors: {
    fallback: "Não consegui responder agora. Tente novamente em instantes.",
    retry: "Tentar novamente",
    countdown: "Você poderá enviar em {seconds}s",
  },
  login: {
    title: "Entrar",
    sessionExpired: "Sua sessão expirou. Entre novamente para continuar.",
    placeholder: "O login estará disponível em breve.",
    backToChat: "Voltar para o chat",
  },
  markdown: {
    close: "Fechar",
    copyLink: "Copiar link",
    externalLinkWarning: "Você está prestes a abrir um site externo.",
    openExternalLink: "Abrir link externo",
    openLink: "Abrir link",
    imageNotAvailable: "Imagem indisponível",
  },
} as const;

export type Messages = typeof ptBR;
