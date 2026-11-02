// pt-BR copy catalog. Its shape (`Messages`) is the contract the `en` catalog must satisfy.
export const ptBR = {
  app: {
    storeName: "Empório da Música",
    assistantName: "Melody",
    tagline: "Atendimento com a Melody",
    title: "Melody · Empório da Música",
    description: "Assistente virtual da Empório da Música",
  },
  theme: {
    toDark: "Ativar tema escuro",
    toLight: "Ativar tema claro",
  },
  language: {
    label: "Idioma",
    pt: "PT",
    en: "EN",
  },
  emptyState: {
    greeting: "Oi! Eu sou a Melody 🎵",
    intro:
      "Assistente virtual do Empório da Música. Posso ajudar com produtos, preços, promoções, formas de pagamento, pedidos e trocas.",
    suggestionsLabel: "Sugestões para começar",
    suggestions: [
      "Quais violões vocês têm até R$ 1.000?",
      "Qual o horário de funcionamento?",
      "Posso parcelar em 12x?",
      "Como faço para devolver um produto?",
    ],
  },
  input: {
    label: "Mensagem para a Melody",
    placeholder: "Pergunte algo à Melody…",
    streamingPlaceholder: "Aguarde a resposta…",
    rateLimitedPlaceholder: "Aguarde {seconds} s para enviar de novo",
    budgetPlaceholder: "Chat pausado até 00:00",
    hint: "Enter envia · Shift+Enter quebra linha",
    send: "Enviar",
    stop: "Parar",
  },
  status: {
    typing: "Melody está digitando…",
    stopped: "Resposta interrompida por você",
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
  // Past-tense labels shown once a tool finishes (same keys as `tools`).
  toolsDone: {
    search_products: "Catálogo consultado",
    get_product: "Produto consultado",
    find_similar_products: "Opções parecidas encontradas",
    get_active_promotions: "Promoções verificadas",
    calculate_payment_options: "Formas de pagamento calculadas",
    get_order_status: "Pedido consultado",
    search_policies: "Política de trocas consultada",
    get_store_info: "Informações da loja consultadas",
    check_return_eligibility: "Possibilidade de troca verificada",
    request_return: "Solicitação de devolução aberta",
    register_complaint: "Reclamação registrada",
    handoff_to_human: "Solicitação registrada",
    fallback: "Consulta concluída",
  },
  toolState: {
    failed: "Não consegui consultar agora",
  },
  availability: {
    in_stock: "Em estoque",
    out_of_stock: "Esgotado",
    coming_soon: "Em breve",
    discontinued: "Descontinuado",
  },
  product: {
    discount: "-{percent}",
    originalPrice: "Preço original: {price}",
  },
  errors: {
    fallback: "Tivemos um problema de conexão. Sua mensagem foi mantida, é só tentar de novo.",
    retry: "Tentar novamente",
    retryIn: "Tentar novamente em {seconds} s",
    serverTitle: "Não consegui responder agora",
    rateLimitedTitle: "Muitas mensagens em pouco tempo",
    rateLimitedDetail: "Aguarde {time} para enviar outra pergunta.",
    rateLimitedReady: "Pronto, você já pode tentar de novo.",
    budgetTitle: "A Melody descansou por hoje",
    budgetDetail:
      "O limite de atendimentos de hoje foi atingido. O chat volta a funcionar às {time} (horário de Campo Grande).",
    budgetResetTime: "00:00",
    droppedTitle: "A resposta foi interrompida",
    droppedDetail: "A conexão caiu antes de a Melody terminar.",
  },
  login: {
    title: "Entrar",
    subtitle: "Converse com a Melody, a assistente virtual da loja.",
    welcomeTitle: "Boas-vindas ao Empório da Música",
    welcomeSubtitle: "Entre para conversar com a Melody.",
    sessionExpired: "Sua sessão expirou",
    sessionExpiredDetail: "Entre de novo para continuar a conversa.",
    username: "Usuário",
    usernamePlaceholder: "Seu usuário",
    password: "Senha",
    passwordPlaceholder: "Sua senha",
    submit: "Entrar",
    submitting: "Entrando…",
    invalidCredentials: "Usuário ou senha inválidos",
    invalidCredentialsDetail: "Confira os dados e tente de novo.",
    locked: "Muitas tentativas",
    lockedDetail:
      "Por segurança, o acesso foi bloqueado temporariamente. Tente de novo mais tarde.",
    noAccount: "Não tem conta? As contas são criadas pela equipe da loja.",
    signOut: "Sair",
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

// Literal pt-BR strings widened to `string` so other catalogs can satisfy the same shape.
type Widen<T> = T extends string
  ? string
  : T extends readonly (infer U)[]
    ? readonly Widen<U>[]
    : { readonly [K in keyof T]: Widen<T[K]> };

export type Messages = Widen<typeof ptBR>;
