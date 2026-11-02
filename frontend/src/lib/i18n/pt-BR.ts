// pt-BR copy catalog. Its shape (`Messages`) is the contract the `en` catalog must satisfy.
export const ptBR = {
  app: {
    storeName: "Empório da Música",
    assistantName: "Melody",
    tagline: "Atendimento com a Melody",
    title: "Melody · Empório da Música",
    description: "Assistente virtual da Empório da Música",
    newChat: "Nova conversa",
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
      "Assistente virtual da Empório da Música. Posso ajudar com produtos, preços, promoções, formas de pagamento, pedidos e trocas.",
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
    find_my_orders: "Buscando seus pedidos…",
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
    find_my_orders: "Pedidos encontrados",
    search_policies: "Políticas da loja consultadas",
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
  // Store home page (`/`). Facts copied from the store policies manual v2.1 (customer-facing
  // sections only); phone, e-mail, address and CNPJ live in `lib/store-info.ts`.
  store: {
    skipToContent: "Pular para o conteúdo",
    nav: {
      label: "Seções da página",
      menu: "Abrir menu",
      closeMenu: "Fechar menu",
      home: "Início",
      about: "Quem somos",
      hours: "Horário",
      contact: "Endereço e contato",
      payment: "Pagamento",
      returns: "Trocas e devoluções",
      shipping: "Frete e entregas",
      promotions: "Promoções",
      warranty: "Garantia",
      privacy: "Privacidade",
    },
    signIn: "Entrar",
    hero: {
      eyebrow: "Instrumentos musicais em Campo Grande – MS",
      title: "Sua música começa aqui.",
      lead: "Loja especializada em instrumentos musicais para músicos iniciantes, intermediários e profissionais.",
      chatCta: "Falar com a Melody",
      visitCta: "Horário e endereço",
      highlights: ["Desde 2008", "Mais de 15 anos de atuação", "Só instrumentos musicais"],
    },
    about: {
      title: "Quem somos",
      paragraphs: [
        "A Empório da Música é uma loja especializada em instrumentos musicais, fundada em 2008 em Campo Grande, Mato Grosso do Sul. Com mais de 15 anos de atuação no mercado, somos referência regional na venda de instrumentos para músicos iniciantes, intermediários e profissionais.",
        "Nosso catálogo reúne instrumentos de marcas nacionais e internacionais: violões, guitarras, baixos, baterias, teclados e ukuleles.",
      ],
      onlyInstrumentsTitle: "Só instrumentos musicais",
      onlyInstruments:
        "Trabalhamos exclusivamente com instrumentos musicais — não comercializamos acessórios como cordas, palhetas, cabos, cases, pedais ou amplificadores.",
      missionTitle: "Missão",
      mission:
        "Democratizar o acesso a instrumentos musicais de qualidade na região Centro-Oeste, oferecendo atendimento especializado e preços competitivos, contribuindo para o desenvolvimento cultural e musical da comunidade.",
    },
    hours: {
      title: "Horário de funcionamento",
      intro:
        "Atendimento presencial na loja. O WhatsApp segue o mesmo horário, com respostas automáticas fora do expediente.",
      dayLabel: "Dia",
      timeLabel: "Horário",
      rows: [
        { day: "Segunda a Sexta-feira", time: "09:00 às 18:00" },
        { day: "Sábado", time: "09:00 às 13:00" },
        { day: "Domingo e Feriados", time: "Fechado" },
      ],
      note: "Em datas especiais (Black Friday, Aniversário da Loja, Natal), o horário pode ser estendido. Alterações são comunicadas com antecedência nas redes sociais e no WhatsApp.",
    },
    contact: {
      title: "Endereço e contato",
      addressLabel: "Endereço",
      postalCode: "CEP {code}",
      phoneLabel: "Telefone (ligações)",
      whatsappLabel: "WhatsApp (mensagens)",
      emailLabel: "E-mail",
    },
    payment: {
      title: "Formas de pagamento",
      intro: "Aceitamos as seguintes formas de pagamento para compras presenciais e online:",
      methods: [
        { name: "PIX", terms: "Pagamento à vista", note: "5% de desconto sobre o preço de tabela" },
        { name: "Cartão de Débito", terms: "Pagamento à vista", note: "Todas as bandeiras aceitas" },
        { name: "Cartão de Crédito", terms: "Até 12x sem juros", note: "Parcela mínima de R$ 100,00" },
        { name: "Boleto Bancário", terms: "Pagamento à vista", note: "Compensação em até 3 dias úteis" },
      ],
      installmentsTitle: "Regras de parcelamento",
      installments: [
        "Parcelamento em até 3x: sem juros, sem valor mínimo de parcela (exceto abaixo de R$ 50,00).",
        "Parcelamento de 4x a 6x: sem juros, parcela mínima de R$ 100,00.",
        "Parcelamento de 7x a 12x: sem juros, parcela mínima de R$ 100,00.",
        "Combinação de formas de pagamento: permitida (ex.: PIX + cartão) para compras acima de R$ 2.000,00.",
      ],
    },
    returns: {
      title: "Trocas e devoluções",
      intro:
        "Seguimos as diretrizes do Código de Defesa do Consumidor (Lei nº 8.078/90) e oferecemos condições claras para trocas e devoluções.",
      groups: [
        {
          title: "Direito de arrependimento (compras online)",
          items: [
            "Você pode solicitar a devolução em até 7 (sete) dias corridos após o recebimento do produto, sem necessidade de justificativa.",
            "O produto deve estar em sua embalagem original, sem sinais de uso, com todos os acessórios e manuais.",
            "O reembolso é realizado na mesma forma de pagamento original em até 10 dias úteis.",
            "O frete de devolução é por conta da loja em caso de arrependimento.",
          ],
        },
        {
          title: "Trocas por defeito",
          items: [
            "Produtos com defeito de fabricação podem ser trocados em até 30 (trinta) dias corridos após a compra.",
            "Após os 30 dias, a garantia deve ser acionada diretamente com o fabricante. A Empório da Música pode intermediar o processo mediante solicitação.",
            "Danos causados por mau uso, quedas, exposição a umidade excessiva ou modificações não autorizadas não são cobertos.",
          ],
        },
        {
          title: "Trocas por preferência",
          items: [
            "Trocas por preferência (cor, modelo, tamanho) são permitidas em até 7 dias, mediante disponibilidade do produto desejado.",
            "O produto deve estar em perfeito estado e na embalagem original.",
            "Diferenças de valor são cobradas ou reembolsadas conforme o caso.",
          ],
        },
        {
          title: "Itens não elegíveis para troca",
          items: [
            "Instrumentos com personalização ou ajustes sob encomenda (setup, regulagem especial).",
            "Produtos adquiridos em promoções de liquidação com aviso explícito de “venda final”.",
            "Boquilhas de instrumentos de sopro, por questões de higiene.",
          ],
        },
      ],
    },
    shipping: {
      title: "Frete e entregas",
      localTitle: "Região metropolitana de Campo Grande",
      local: [
        "Frete grátis para pedidos acima de R$ 500,00.",
        "Para pedidos abaixo de R$ 500,00, taxa fixa de R$ 35,00.",
        "Prazo de entrega: 1 a 3 dias úteis.",
        "Entrega realizada por motoboy próprio. Você será contactado por telefone antes da entrega.",
      ],
      otherTitle: "Outras cidades",
      otherIntro:
        "Utilizamos os serviços dos Correios (PAC e SEDEX) e da transportadora Jadlog para envios fora da região metropolitana de Campo Grande.",
      estimateLabel: "Prazo estimado",
      trackingLabel: "Rastreamento",
      insuranceLabel: "Seguro",
      carriers: [
        { name: "PAC (Correios)", estimate: "5 a 12 dias úteis", tracking: "Sim", insurance: "Incluído" },
        { name: "SEDEX (Correios)", estimate: "2 a 5 dias úteis", tracking: "Sim", insurance: "Incluído" },
        { name: "Jadlog (.package)", estimate: "3 a 8 dias úteis", tracking: "Sim", insurance: "Incluído" },
      ],
      notes: [
        "O valor do frete é calculado automaticamente com base no CEP de destino, peso e dimensões do produto. Instrumentos de grande porte (baterias acústicas, pianos digitais, contrabaixos) podem exigir frete especial com cotação individual.",
        "Todos os envios incluem seguro contra extravios e danos durante o transporte. Em caso de avaria, recuse o recebimento e entre em contato imediatamente com a loja.",
        "O código de rastreamento é enviado automaticamente por e-mail e WhatsApp assim que o pedido é despachado, e pode ser consultado no site dos Correios ou da Jadlog.",
      ],
    },
    promotions: {
      title: "Promoções",
      intro: "Realizamos promoções periódicas ao longo do ano. As principais campanhas incluem:",
      campaigns: [
        { name: "Aniversário da Loja", when: "Agosto", detail: "Descontos de 10% a 25% em itens selecionados." },
        { name: "Black Friday", when: "Novembro", detail: "Descontos de 15% a 30% em todo o catálogo." },
        { name: "Volta às Aulas", when: "Fevereiro", detail: "Descontos especiais em instrumentos para estudantes." },
        { name: "Queima de Estoque", when: "Pontual", detail: "Promoções pontuais para renovação de catálogo." },
        { name: "Semana do Músico", when: "Novembro", detail: "Promoções na semana do Dia do Músico (22 de novembro)." },
      ],
      rulesTitle: "Regras",
      rules: [
        "Promoções não são cumulativas. O desconto de PIX (5%) não se aplica sobre preços já promocionais.",
        "Promoções estão sujeitas à disponibilidade de estoque. Produtos esgotados durante a promoção não geram direito a reserva de preço.",
      ],
    },
    warranty: {
      title: "Garantia",
      legalTitle: "Garantia legal",
      legal:
        "Conforme o Código de Defesa do Consumidor, todos os produtos possuem garantia legal de 90 (noventa) dias contra defeitos de fabricação, contados a partir da data de recebimento.",
      makerTitle: "Garantia do fabricante",
      maker:
        "Além da garantia legal, a maioria dos fabricantes oferece garantia própria que pode variar de 6 meses a 2 anos. Os prazos e condições específicos estão no certificado de garantia que acompanha cada produto.",
      excludedTitle: "O que a garantia não cobre",
      excluded: [
        "Desgaste natural de peças (trastes, cordas, feltros, palhetas de sopro).",
        "Danos por mau uso, queda, exposição a condições climáticas extremas.",
        "Modificações ou reparos realizados por terceiros não autorizados.",
        "Danos estéticos que não afetem a funcionalidade do instrumento.",
      ],
    },
    privacy: {
      title: "Privacidade e proteção de dados",
      intro:
        "A Empório da Música está em conformidade com a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018). Os dados pessoais coletados durante o atendimento (nome, telefone, e-mail, endereço) são utilizados exclusivamente para:",
      uses: [
        "Processamento e entrega de pedidos.",
        "Comunicação sobre status de pedidos e rastreamento.",
        "Envio de promoções e novidades (mediante seu consentimento explícito).",
        "Cumprimento de obrigações legais e fiscais.",
      ],
      sharing: "Dados de clientes não são compartilhados com terceiros para fins de marketing.",
      deletion: "Você pode solicitar a exclusão dos seus dados a qualquer momento pelo WhatsApp ou e-mail.",
    },
    footer: {
      contactTitle: "Contato",
      sectionsTitle: "Nesta página",
      legalNameLabel: "Razão social",
      cnpjLabel: "CNPJ",
    },
  },
  // Chat widget on the store page: side panel (desktop) or full-screen sheet (mobile) + FAB.
  widget: {
    open: "Abrir chat com a Melody",
    openUnread: "Abrir chat com a Melody (nova mensagem)",
    minimize: "Minimizar chat",
    maximize: "Maximizar chat",
    restore: "Restaurar tamanho do chat",
    panelLabel: "Chat com a Melody",
    title: "Melody",
    subtitle: "Assistente virtual da loja",
    signInCta: "Entrar para conversar",
    loading: "Carregando o chat…",
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
