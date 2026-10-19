"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, ChefHat, CircleAlert, LoaderCircle, Play, Search, X } from "lucide-react";
import { api } from "@/lib/api";
import { formatQuantidade } from "@/lib/utils";
import { KitchenDayOverview, KitchenProductionQueue } from "@/components/shared/kitchen-operations";
import { KitchenIngredients, type KitchenIngredient } from "@/components/shared/kitchen-ingredients";
import { KitchenChecklist } from "@/components/shared/kitchen-checklist";
import { MarkdownContent } from "@/components/shared/markdown-content";
import { useAuthStore } from "@/stores/use-auth-store";

type SearchItem = { recipe_id: string; name: string };
type KitchenBlock = { id: string; section: string; title: string; markdown: string; checkable?: boolean };
type Projection = {
  session_id?: string;
  completed_block_ids?: string[];
  checked_ingredient_ids?: string[];
  recipe_id: string;
  recipe_version: string;
  name: string;
  yield_quantity: string;
  yield_unit: string;
  ingredients: KitchenIngredient[];
  blocks: KitchenBlock[];
  warnings: string[];
};
type Station = {
  id: string;
  name: string;
  status: "active" | "paused" | "closed";
  revision: number;
  recipe_id: string | null;
  section: "ingredients" | "preparation" | "steps" | "assembly";
  block_index: number;
  speech_part_index: number;
  rendered_revision: number | null;
  projection: Projection | null;
  notice: string | null;
};
type Receipt = {
  revision: number;
  status: string;
  selection?: { items: SearchItem[]; next_offset: number | null; selection_id: string } | null;
};
type AlexaLink = {
  linked: boolean;
  station_id: string | null;
  pending_devices: { id: string; first_seen_at: string }[];
  approved_device_id: string | null;
};

function commandId(): string {
  try {
    return window.crypto.randomUUID();
  } catch {
    // Older browsers may not expose randomUUID on a local non-HTTPS origin.
  }
  const bytes = new Uint8Array(16);
  window.crypto.getRandomValues(bytes);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, value => value.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export default function CozinhaPage() {
  const queryClient = useQueryClient();
  const usuarioId = useAuthStore(state => state.usuario?.id ?? "anonimo");
  const autenticada = useAuthStore(state => state.isAuthenticated);
  const [manageAlexa, setManageAlexa] = useState(false);
  const [leaseId, setLeaseId] = useState<string | null>(null);
  const [takeover, setTakeover] = useState(false);
  const [browserOnline, setBrowserOnline] = useState(true);
  const [pageVisible, setPageVisible] = useState(true);
  const [heartbeatFailed, setHeartbeatFailed] = useState(false);
  const [nomeEstacao, setNomeEstacao] = useState("Minha cozinha");
  const [termo, setTermo] = useState("");
  const [busca, setBusca] = useState("");
  const [offsetBusca, setOffsetBusca] = useState(0);
  const [aviso, setAviso] = useState<string | null>(null);
  const [loadingCommand, setLoadingCommand] = useState(false);
  const commandPending = useRef(false);
  const recipeHeader = useRef<HTMLElement>(null);
  const [focusRecipe, setFocusRecipe] = useState(0);
  const [optimisticIngredients, setOptimisticIngredients] = useState<string[] | null>(null);
  const [optimisticCompleted, setOptimisticCompleted] = useState<string[] | null>(null);

  const stationsQuery = useQuery({
    queryKey: ["cozinha", usuarioId, "stations"],
    queryFn: async () => (await api.get<{ items: { id: string; name: string; status: Station["status"]; revision: number }[] }>("/cozinha/stations")).data,
    staleTime: 0,
  });
  const alexaLinkQuery = useQuery({
    queryKey: ["cozinha", usuarioId, "alexa-link"],
    queryFn: async () => (await api.get<AlexaLink>("/cozinha/alexa/link")).data,
    enabled: autenticada,
    staleTime: 0,
  });
  const alexaConfigured = Boolean(alexaLinkQuery.data?.linked && alexaLinkQuery.data.approved_device_id && alexaLinkQuery.data.station_id);
  const showAlexaSetup = Boolean(alexaLinkQuery.data && (!alexaConfigured || manageAlexa));
  const stationId = stationsQuery.data?.items[0]?.id ?? null;
  const stationQuery = useQuery({
    queryKey: ["cozinha", usuarioId, "station", stationId],
    enabled: Boolean(stationId && leaseId),
    queryFn: async () => {
      const current = queryClient.getQueryData<Station>(["cozinha", usuarioId, "station", stationId]);
      const result = await api.get<{ changed: boolean; station: Station | null }>(`/cozinha/stations/${stationId}`, {
        params: { lease_id: leaseId, after_revision: current?.revision },
      });
      const latest = queryClient.getQueryData<Station>(["cozinha", usuarioId, "station", stationId]);
      if (!result.data.changed || !result.data.station) return latest ?? current ?? null;
      return latest && result.data.station.revision < latest.revision
        ? latest
        : result.data.station;
    },
    refetchInterval: 2000,
    refetchIntervalInBackground: false,
    staleTime: 0,
  });
  const searchQuery = useQuery({
    queryKey: ["cozinha", usuarioId, "recipe-search", busca, offsetBusca],
    enabled: Boolean(busca),
    queryFn: async () => (await api.get<{ items: SearchItem[]; next_offset: number | null }>("/cozinha/recipes/search", {
      params: { q: busca, offset: offsetBusca },
    })).data,
    staleTime: 0,
  });
  const station = stationQuery.data;
  const remoteUnavailable = !browserOnline || !pageVisible || heartbeatFailed || stationQuery.isError;
  const activeBlocks = useMemo(
    () => station?.projection?.blocks.filter(block => block.section === station.section) ?? [],
    [station?.projection, station?.section],
  );
  const currentBlock = activeBlocks[station?.block_index ?? 0];
  const showingPreparation = station?.section === "preparation" || station?.section === "steps";
  const preparationText = station?.projection?.blocks.find(block => block.section === "preparation");

  const navigationSections = ([
    { section: "ingredients", label: "ingredientes" },
    { section: preparationText ? "preparation" : "steps", label: "modo de preparo" },
    { section: "assembly", label: "montagem" },
  ] as const).filter(item => station?.projection?.blocks.some(block => block.section === item.section));
  const sectionIndex = navigationSections.findIndex(item => showingPreparation ? item.section === "preparation" || item.section === "steps" : item.section === station?.section);
  const previousSection = navigationSections[sectionIndex - 1];
  const nextSection = navigationSections[sectionIndex + 1];
  const assemblyPrevious = station?.section === "assembly" && station.block_index > 0;
  const assemblyNext = station?.section === "assembly" && station.block_index < activeBlocks.length - 1;

  useEffect(() => {
    if (!station?.projection || !leaseId) return;
    setBusca(""); setTermo(""); setOffsetBusca(0);
    // Wait for the search results and expanded queue to leave the layout.
    const frame = window.requestAnimationFrame(() => {
      recipeHeader.current?.focus({ preventScroll: true });
      recipeHeader.current?.scrollIntoView?.({ block: "start", behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [station?.projection?.recipe_id, focusRecipe, leaseId]);

  const invalidateStation = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["cozinha", usuarioId, "stations"] }),
      queryClient.invalidateQueries({ queryKey: ["cozinha", usuarioId, "station", stationId] }),
    ]);
  }, [queryClient, stationId, usuarioId]);

  useEffect(() => {
    if (autenticada) return;
    if (stationId && leaseId) {
      void api.post(`/cozinha/stations/${stationId}/close`, { lease_id: leaseId }).catch(() => undefined);
    }
    setLeaseId(null);
    queryClient.removeQueries({ queryKey: ["cozinha", usuarioId] });
  }, [autenticada, queryClient, usuarioId, stationId, leaseId]);

  useEffect(() => {
    const online = () => setBrowserOnline(true);
    const offline = () => setBrowserOnline(false);
    window.addEventListener("online", online);
    window.addEventListener("offline", offline);
    setBrowserOnline(window.navigator.onLine);
    return () => {
      window.removeEventListener("online", online);
      window.removeEventListener("offline", offline);
    };
  }, []);

  useEffect(() => {
    const visibility = () => setPageVisible(document.visibilityState === "visible");
    document.addEventListener("visibilitychange", visibility);
    visibility();
    return () => document.removeEventListener("visibilitychange", visibility);
  }, []);

  useEffect(() => {
    if (!stationId || !leaseId) return;
    const sendHeartbeat = async () => {
      if (document.visibilityState !== "visible") return;
      try {
        await api.post(`/cozinha/stations/${stationId}/heartbeat`, { lease_id: leaseId });
        setHeartbeatFailed(false);
      } catch (error) {
        const status = (error as { response?: { status?: number } }).response?.status;
        setHeartbeatFailed(status !== 409);
        if (status === 409) {
          setLeaseId(null);
          setTakeover(true);
          setAviso("A estação pausou enquanto a tela estava suspensa. Retome para continuar.");
          void stationsQuery.refetch();
        }
      }
    };
    const heartbeat = window.setInterval(() => {
      void sendHeartbeat();
    }, 10_000);
    const onVisibility = () => {
      if (document.visibilityState === "visible") void sendHeartbeat();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(heartbeat);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [stationId, leaseId, stationsQuery.refetch]);

  useEffect(() => {
    if (!station || !leaseId || station.revision <= (station.rendered_revision ?? 0)) return;
    const revision = station.revision;
    void api.post<{ rendered_revision: number }>(`/cozinha/stations/${station.id}/ack`, { lease_id: leaseId, revision })
      .then(({ data }) => queryClient.setQueryData<Station>(["cozinha", usuarioId, "station", station.id], previous =>
        previous ? { ...previous, rendered_revision: data.rendered_revision } : previous,
      ))
      .catch(() => undefined);
  }, [station?.id, station?.revision, station?.rendered_revision, leaseId, queryClient, station, usuarioId]);

  const activate = async (assume: boolean) => {
    if (!stationId || !browserOnline) return;
    setAviso(null);
    try {
      const latest = await stationsQuery.refetch();
      const currentRevision = latest.data?.items[0]?.revision ?? stationQuery.data?.revision ?? 0;
      const { data } = await api.post<{ lease_id: string; station: Station }>(`/cozinha/stations/${stationId}/lease`, {
        expected_revision: currentRevision,
        takeover: assume,
      });
      setLeaseId(data.lease_id);
      setTakeover(false);
      setHeartbeatFailed(false);
      queryClient.setQueryData(["cozinha", usuarioId, "station", stationId], data.station);
    } catch (error) {
      const status = (error as { response?: { status?: number } }).response?.status;
      setTakeover(status === 409);
      setAviso(status === 409 ? "A estação já está aberta em outra tela ou mudou. Você pode retomá-la aqui." : "Não foi possível ativar a estação.");
      if (status === 409) await stationsQuery.refetch();
    }
  };

  const sendCommand = async (type: string, extras: Record<string, unknown> = {}) => {
    if (!station || !leaseId || commandPending.current || remoteUnavailable) return;
    commandPending.current = true;
    if (type === "set_ingredient_checked") {
      const ids = new Set(station.projection?.checked_ingredient_ids ?? []);
      if (extras.completed) ids.add(String(extras.block_id)); else ids.delete(String(extras.block_id));
      setOptimisticIngredients([...ids]);
    }
    if (type === "reset_steps") setOptimisticCompleted([]);
    if (type === "set_step_completed") {
      const ids = new Set(station.projection?.completed_block_ids ?? []);
      if (extras.completed) ids.add(String(extras.block_id));
      else ids.delete(String(extras.block_id));
      setOptimisticCompleted([...ids]);
    }
    setLoadingCommand(true);
    setAviso(null);
    try {
      const { data } = await api.post<Receipt>(`/cozinha/stations/${station.id}/commands`, {
        command_id: commandId(), expected_revision: station.revision, lease_id: leaseId, type, payload: extras,
      });
      if (data.status === "no_results") setAviso("Não encontrei essa receita. Confira o nome e tente novamente.");
      else if (data.status === "selection_required") setAviso("Encontrei mais de uma receita. Escolha na lista da tela.");
      await invalidateStation();
      if (["open_recipe", "show_section", "next", "previous"].includes(type) && data.status === "accepted") setFocusRecipe(current => current + 1);
    } catch (error) {
      const status = (error as { response?: { status?: number } }).response?.status;
      setAviso(status === 409 ? "A estação foi atualizada. Aguarde a tela sincronizar e tente de novo." : "Não foi possível concluir. Verifique a conexão e tente novamente.");
      await invalidateStation();
    } finally {
      commandPending.current = false;
      setOptimisticCompleted(null);
      setOptimisticIngredients(null);
      setLoadingCommand(false);
    }
  };

  const createStation = async () => {
    try {
      await api.post("/cozinha/stations", { name: nomeEstacao.trim() || "Minha cozinha" });
      await stationsQuery.refetch();
    } catch {
      setAviso("Não foi possível criar a estação. Tente novamente.");
    }
  };

  const confirmAlexaDevice = async (pendingDeviceId: string) => {
    try {
      await api.put("/cozinha/alexa/link/device", { pending_device_id: pendingDeviceId });
      await alexaLinkQuery.refetch();
      setAviso("Echo confirmada. Agora selecione a estação que ficará aberta no Chrome.");
    } catch {
      setAviso("O pedido da Echo venceu. Peça novamente à Alexa e confirme em até cinco minutos.");
    }
  };

  const chooseAlexaStation = async (selectedStationId: string) => {
    try {
      await api.put("/cozinha/alexa/link/station", { station_id: selectedStationId });
      await alexaLinkQuery.refetch();
      setAviso("Estação vinculada à Alexa. A tela Chrome precisa estar ativa para receber receitas.");
    } catch {
      setAviso("Não foi possível vincular esta estação. Atualize a página e tente novamente.");
    }
  };

  const unlinkAlexa = async () => {
    try {
      await api.delete("/cozinha/alexa/link");
      await alexaLinkQuery.refetch();
      setAviso("Conta Alexa desvinculada.");
    } catch {
      setAviso("Não foi possível desvincular a Alexa. Tente novamente.");
    }
  };

  const closeStation = async () => {
    if (!stationId || !leaseId) return;
    try {
      await api.post(`/cozinha/stations/${stationId}/close`, { lease_id: leaseId });
    } catch {
      setAviso("Não foi possível pausar a estação. A lease será encerrada automaticamente em até 30 segundos.");
    } finally {
      setLeaseId(null);
      setTakeover(false);
      await invalidateStation();
    }
  };

  const doSearch = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setOffsetBusca(0);
    setBusca(termo.trim());
  };

  if (stationsQuery.isLoading) return <div className="p-8 text-center" role="status">Carregando modo cozinha…</div>;

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-widest text-primary">Fornada · produção</p>
          <h1 className="mt-1 text-3xl font-bold sm:text-4xl">Modo cozinha</h1>
          <p className="mt-2 text-base text-muted-foreground">Receitas bem à vista, para acompanhar o preparo.</p>
        </div>
        {station && leaseId && <button type="button" onClick={closeStation} className="inline-flex min-h-12 items-center gap-2 rounded-xl border px-4 text-base font-semibold hover:bg-muted">
          <X className="h-5 w-5" /> Pausar estação
        </button>}
      </div>

      {alexaConfigured && <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground"><span>Alexa conectada</span><button type="button" className="min-h-12 rounded-xl px-4 font-semibold text-primary hover:bg-muted" onClick={() => setManageAlexa(current => !current)}>{manageAlexa ? "Fechar ajustes da Alexa" : "Gerenciar Alexa"}</button></div>}
      {alexaLinkQuery.isError && <p role="alert">Não foi possível consultar a conexão da Alexa. <button type="button" className="min-h-12 px-3 font-semibold text-primary" onClick={() => void alexaLinkQuery.refetch()}>Tentar novamente</button></p>}
      {showAlexaSetup && <details className="rounded-2xl border bg-card p-5 sm:p-6">
        <summary className="cursor-pointer text-lg font-semibold">Como configurar a Alexa na Echo Dot 3</summary>
        <div className="mt-4 space-y-3 text-sm text-muted-foreground">
          <p>O Fornada já tem o receptor e a validação dos pedidos Alexa. Para conectar, cadastre a skill na Amazon e configure as credenciais no servidor conforme os passos abaixo.</p>
          <ol className="list-decimal space-y-2 pl-5">
            <li>Na <a className="font-medium text-primary underline" href="https://developer.amazon.com/alexa/console/ask" target="_blank" rel="noreferrer">Alexa Developer Console</a>, crie uma skill personalizada no idioma Português (Brasil), com nome de invocação <strong>cozinha fornada</strong>. Em Endpoint, selecione HTTPS e use a URL abaixo.</li>
            <li>Importe o modelo de interação pt-BR do Fornada e clique em salvar e compilar.</li>
            <li>Em Account Linking, escolha Authorization Code Grant. Use os endereços abaixo, autenticação do cliente HTTP Basic e os escopos <code>cozinha:read cozinha:control</code>. Copie as Redirect URLs mostradas pela Amazon sem alterá-las.</li>
            <li>Na configuração do servidor, preencha o ID da skill exibido pela Amazon, gere um ID e segredo OAuth próprios, cadastre todas as Redirect URLs copiadas e ative <code>ALEXA_ENABLED=true</code>. Depois, reinicie/deploy a API.</li>
            <li>No app Alexa, habilite a skill de desenvolvimento e vincule sua conta Fornada. Abra esta tela no Chrome, crie/ative uma estação e diga: <strong>“Alexa, abrir cozinha fornada”</strong>. Confirme aqui a Echo que aparecer e escolha a estação.</li>
          </ol>
          <div className="space-y-1 rounded-xl bg-muted/50 p-3 font-mono text-xs text-foreground sm:text-sm">
            <p>Endpoint da skill: https://fornada.atospd.com/api/v1/integrations/alexa/requests</p>
            <p>Authorization URI: https://fornada.atospd.com/api/v1/integrations/alexa/oauth/authorize</p>
            <p>Access Token URI: https://fornada.atospd.com/api/v1/integrations/alexa/oauth/token</p>
          </div>
          <p>A Amazon identifica a skill pelo ID validado em cada pedido. Na primeira chamada vinculada, o Fornada identifica a Echo por um código interno temporário; confirme a Echo nesta tela para autorizar o controle da estação. O ID do dispositivo não é mostrado.</p>
        </div>
      </details>}

      {showAlexaSetup && alexaLinkQuery.data?.linked && <section className="rounded-2xl border bg-card p-5 sm:p-6">
        <h2 className="text-xl font-semibold">Alexa · Echo Dot</h2>
        <p className="mt-2 text-base text-muted-foreground">Confirme a Echo que pediu acesso e escolha qual estação ativa receberá as receitas.</p>
        {alexaLinkQuery.data.pending_devices.map(device => <div key={device.id} className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-muted/40 p-4">
          <span className="text-base">Echo solicitada às {new Date(device.first_seen_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span>
          <button type="button" onClick={() => void confirmAlexaDevice(device.id)} className="min-h-12 rounded-xl bg-primary px-5 font-semibold text-primary-foreground">Confirmar esta Echo</button>
        </div>)}
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
          {alexaLinkQuery.data.approved_device_id && <label className="flex-1 text-base font-medium" htmlFor="alexa-station">Estação vinculada
            <select id="alexa-station" value={alexaLinkQuery.data.station_id ?? ""} onChange={event => void chooseAlexaStation(event.target.value)} className="mt-2 min-h-12 w-full rounded-xl border bg-background px-3">
              <option value="" disabled>Escolha uma estação</option>
              {stationsQuery.data?.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>}
          <button type="button" onClick={() => void unlinkAlexa()} className="min-h-12 rounded-xl border px-5 font-semibold">Desvincular conta Alexa</button>
        </div>
      </section>}

      {aviso && <div role="status" className="flex items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-base text-amber-950"><CircleAlert className="mt-0.5 h-5 w-5 shrink-0" /><p>{aviso}</p></div>}
      {remoteUnavailable && leaseId && <div role="alert" className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-base text-amber-950">
        {!browserOnline ? "Sem conexão. A receita que ficou na tela pode estar desatualizada; os comandos estão pausados." : stationQuery.isError || heartbeatFailed ? "Não foi possível confirmar o estado atual. A receita pode estar desatualizada e os comandos estão pausados." : "A tela está em segundo plano. Volte para confirmar a estação e retomar os comandos."}
      </div>}

      {autenticada && <KitchenDayOverview recipeOpen={Boolean(station?.projection && leaseId)} />}

      {!stationId ? <section className="rounded-2xl border bg-card p-6 sm:p-8">
        <ChefHat className="h-10 w-10 text-primary" />
        <h2 className="mt-4 text-2xl font-semibold">Prepare sua estação</h2>
        <p className="mt-2 text-base text-muted-foreground">Dê um nome para a tela que ficará na cozinha.</p>
        <div className="mt-5 flex flex-col gap-3 sm:flex-row">
          <label className="sr-only" htmlFor="nome-estacao">Nome da estação</label>
          <input id="nome-estacao" maxLength={80} value={nomeEstacao} onChange={event => setNomeEstacao(event.target.value)} className="min-h-12 min-w-0 flex-1 rounded-xl border bg-background px-4 text-lg" />
          <button type="button" onClick={createStation} className="min-h-12 rounded-xl bg-primary px-6 text-base font-semibold text-primary-foreground">Criar estação</button>
        </div>
      </section> : !leaseId ? <section className="rounded-2xl border bg-card p-6 sm:p-8">
        <ChefHat className="h-10 w-10 text-primary" />
        <h2 className="mt-4 text-2xl font-semibold">{takeover ? "Retomar esta estação?" : "Estação pronta"}</h2>
        <p className="mt-2 text-base text-muted-foreground">{takeover ? "Ela pode estar aberta em outra aba. Ao retomar, essa tela passa a controlar a estação." : "Ative a tela para escolher uma receita e acompanhar o preparo."}</p>
        <button type="button" disabled={!browserOnline} onClick={() => void activate(takeover)} className="mt-5 inline-flex min-h-14 items-center gap-3 rounded-xl bg-primary px-6 text-lg font-semibold text-primary-foreground disabled:opacity-50">
          <Play className="h-5 w-5" /> {takeover ? "Retomar nesta tela" : "Ativar modo cozinha"}
        </button>
      </section> : !station ? <div role="status" className="rounded-xl border p-6">Sincronizando a estação…</div> : <>
        <section className="rounded-2xl border bg-card p-5 sm:p-8">
          <form onSubmit={doSearch} className="flex flex-col gap-3 sm:flex-row">
            <label className="sr-only" htmlFor="buscar-receita">Buscar receita</label>
            <div className="relative min-w-0 flex-1"><Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <input id="buscar-receita" value={termo} onChange={event => setTermo(event.target.value)} placeholder="Busque uma OP ou receita para preparar" className="min-h-14 w-full rounded-xl border bg-background pl-12 pr-4 text-lg" />
            </div>
            <button type="submit" disabled={!termo.trim() || remoteUnavailable} className="min-h-14 rounded-xl bg-primary px-7 text-lg font-semibold text-primary-foreground disabled:opacity-50">Buscar</button>
          </form>
          <KitchenProductionQueue search={termo} recipeOpen={Boolean(station.projection)} disabled={loadingCommand || remoteUnavailable} onOpen={recipe_id => void sendCommand("open_recipe", { recipe_id })} />
          {busca && <div className="mt-5 space-y-2" aria-live="polite">
            {searchQuery.isFetching && <p className="text-base text-muted-foreground">Procurando receitas…</p>}
            {searchQuery.data?.items.length === 0 && !searchQuery.isFetching && <p className="rounded-xl bg-muted p-4 text-base">Nenhuma receita encontrada para “{busca}”.</p>}
            {searchQuery.data && <h2 className="text-lg font-semibold">Outras receitas</h2>}
            {searchQuery.data?.items.map((item, index) => <button type="button" key={item.recipe_id} disabled={loadingCommand || remoteUnavailable} onClick={() => void sendCommand("open_recipe", { recipe_id: item.recipe_id })} className="flex min-h-14 w-full items-center justify-between rounded-xl border px-4 text-left text-lg font-medium hover:border-primary hover:bg-muted disabled:opacity-50">
              <span>{item.name}</span><span className="text-sm font-normal text-muted-foreground">Abrir</span>
            </button>)}
            {searchQuery.data?.next_offset !== null && searchQuery.data?.next_offset !== undefined && <button type="button" onClick={() => setOffsetBusca(searchQuery.data?.next_offset ?? 0)} className="min-h-12 px-4 text-base font-semibold text-primary">Ver mais receitas</button>}
          </div>}
        </section>

        {station.projection ? <section className="space-y-5">
          <header ref={recipeHeader} tabIndex={-1} aria-label="Receita aberta" className="scroll-mt-20 rounded-2xl border bg-card p-5 outline-none sm:p-8">
            <p className="text-sm font-medium uppercase tracking-widest text-primary">Receita aberta</p>
            <h2 className="mt-2 break-words text-3xl font-bold sm:text-4xl">{station.projection.name}</h2>
            <p className="mt-2 text-lg text-muted-foreground">Rende {formatQuantidade(station.projection.yield_quantity)} {station.projection.yield_unit}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {([ ["ingredients", "Ingredientes"], ["preparation", "Modo de preparo"], ["assembly", "Montagem"] ] as const).map(([section, label]) => {
                const targetSection = section === "preparation" && !preparationText ? "steps" : section;
                const available = station.projection?.blocks.some(block => block.section === targetSection);
                const selected = section === "preparation" ? showingPreparation : station.section === section;
                return <button type="button" key={section} disabled={!available || loadingCommand || remoteUnavailable} onClick={() => void sendCommand("show_section", { section: targetSection })} className={`min-h-12 rounded-xl border px-5 text-base font-semibold disabled:cursor-not-allowed disabled:opacity-40 ${selected ? "border-primary bg-primary text-primary-foreground" : "hover:bg-muted"}`}>{label}</button>;
              })}
            </div>
          </header>

          {station.projection.warnings.map((warning, index) => <div key={`${warning}-${index}`} className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-base text-amber-950">{warning}</div>)}
          {showingPreparation && <section id="modo-de-preparo" aria-label="Modo de preparo" className="scroll-mt-6 space-y-5">
            <article className="rounded-2xl border bg-card p-5 sm:p-8">
              <h3 className="text-2xl font-bold sm:text-3xl">Modo de preparo</h3>
              {preparationText ? <MarkdownContent className="mt-6 text-xl leading-relaxed sm:text-2xl">{preparationText.markdown}</MarkdownContent> : <p className="mt-4 text-lg text-muted-foreground">Acompanhe o preparo nas etapas abaixo.</p>}
            </article>
          <KitchenChecklist blocks={station.projection.blocks} completedIds={optimisticCompleted ?? station.projection.completed_block_ids ?? []} section="preparation" currentId={currentBlock?.id} disabled={loadingCommand || remoteUnavailable} onComplete={(block_id, completed) => void sendCommand("set_step_completed", { block_id, completed })} onReset={() => void sendCommand("reset_steps")} />
            <a href="#modo-de-preparo" className="inline-flex min-h-12 items-center rounded-xl px-4 font-semibold text-primary hover:bg-muted">Voltar ao início do modo de preparo</a>
          </section>}
          {!showingPreparation && (currentBlock ? <article className="min-h-64 rounded-2xl border bg-card p-5 sm:p-8" aria-live="polite">
            <p className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">{station.section === "ingredients" ? "Lista da receita" : "Leitura da receita"}</p>
            <h3 className="mt-2 text-2xl font-bold sm:text-3xl">{currentBlock.title}</h3>
            {station.section === "ingredients" ? <KitchenIngredients ingredients={station.projection.ingredients} checkedIds={optimisticIngredients ?? station.projection.checked_ingredient_ids ?? []} disabled={loadingCommand || remoteUnavailable} onCheck={(block_id, completed) => void sendCommand("set_ingredient_checked", { block_id, completed })} /> : <MarkdownContent className="mt-6 text-xl leading-relaxed sm:text-2xl">{currentBlock.markdown}</MarkdownContent>}
          </article> : <article className="rounded-2xl border border-dashed bg-card p-8 text-center"><p className="text-xl font-semibold">Esta receita ainda não tem conteúdo nesta seção.</p><p className="mt-2 text-base text-muted-foreground">Você pode continuar consultando as outras seções.</p></article>)}

          <nav aria-label="Navegação da receita" className="flex flex-wrap items-center justify-between gap-3 pb-6">
            {(assemblyPrevious || previousSection) && <button type="button" disabled={loadingCommand || remoteUnavailable} onClick={() => void (assemblyPrevious ? sendCommand("previous") : sendCommand("show_section", { section: previousSection.section }))} className="inline-flex min-h-14 items-center justify-center gap-3 rounded-xl border bg-card px-5 text-lg font-semibold disabled:opacity-40"><ArrowLeft className="h-5 w-5" />{assemblyPrevious ? "Montagem anterior" : `Voltar para ${previousSection.label}`}</button>}
            <button type="button" disabled={!currentBlock || loadingCommand || remoteUnavailable} onClick={() => void sendCommand("repeat")} className="min-h-12 rounded-xl px-4 text-base font-semibold text-primary hover:bg-muted">{showingPreparation ? "Repetir leitura" : "Repetir"}</button>
            {(assemblyNext || nextSection) && <button type="button" disabled={loadingCommand || remoteUnavailable} onClick={() => void (assemblyNext ? sendCommand("next") : sendCommand("show_section", { section: nextSection.section }))} className="inline-flex min-h-14 items-center justify-center gap-3 rounded-xl bg-primary px-5 text-lg font-semibold text-primary-foreground disabled:opacity-40">{assemblyNext ? "Próxima montagem" : `Ir para ${nextSection.label}`}<ArrowRight className="h-5 w-5" /></button>}
          </nav>
        </section> : <section className="rounded-2xl border border-dashed bg-card p-10 text-center">
          {station.notice && <p role="status" className="mb-4 rounded-xl border border-amber-300 bg-amber-50 p-4 text-base text-amber-950">{station.notice}</p>}
          <ChefHat className="mx-auto h-12 w-12 text-muted-foreground" /><h2 className="mt-4 text-2xl font-semibold">Escolha uma receita</h2><p className="mt-2 text-base text-muted-foreground">A receita e a etapa ficam salvas para você retomar depois.</p>
        </section>}
        {loadingCommand && <p className="flex items-center justify-center gap-2 text-base text-muted-foreground" role="status"><LoaderCircle className="h-4 w-4 animate-spin" />Atualizando estação…</p>}
      </>}
    </div>
  );
}
