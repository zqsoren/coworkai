import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useStore } from "@/store"
import { translations } from "@/lib/i18n"
import { Loader2 } from "lucide-react"
import type { OutputMode } from "@/lib/api"

interface Props {
    open: boolean
    onOpenChange: (open: boolean) => void
}

export function AgentSettingsModal({ open, onOpenChange }: Props) {
    const { language, currentAgentId, agents, updateAgent } = useStore()
    const t = translations[language].agentSettings

    const [name, setName] = useState("")
    const [prompt, setPrompt] = useState("")
    const [model, setModel] = useState("")
    const [providerId, setProviderId] = useState("")
    const [personaMode, setPersonaMode] = useState("normal")

    const [providers, setProviders] = useState<any[]>([])
    const [outputModes, setOutputModes] = useState<OutputMode[]>([])
    const [isSaving, setIsSaving] = useState(false)

    const agent = agents.find(a => a.id === currentAgentId)
    const selectedProvider = providers.find(p => p.id === providerId)

    useEffect(() => {
        if (open && currentAgentId) {
            if (agent) {
                setName(agent.name)
                setPrompt(agent.system_prompt || "")
                if (agent.provider_id) {
                    setProviderId(agent.provider_id)
                }
                if (agent.model_name) setModel(agent.model_name)
                if (agent.persona_mode) setPersonaMode(agent.persona_mode)
            } else {
                setName("")
                setPrompt("")
                setProviderId("")
                setModel("")
                setPersonaMode("normal") // default internal mode
            }
            loadProviders()
            loadOutputModes()
        }
    }, [open, currentAgentId, agents])

    // Auto-sync model from provider if none is explicitly overridden
    useEffect(() => {
        if (open && selectedProvider) {
            // If agent is not defined (e.g., new agent creation, though this modal is for existing)
            // or if the model is empty, set it to the provider's default.
            if (!agent || !agent.model_name) {
                setModel(selectedProvider.models?.[0] || "")
            } else if (agent.provider_id !== selectedProvider.id) {
                // If the provider changes during an edit, update the model preview to the new provider's default
                setModel(selectedProvider.models?.[0] || "")
            } else {
                // If agent and provider match, and agent has a model, keep it.
                setModel(agent.model_name || selectedProvider.models?.[0] || "")
            }
        }
    }, [selectedProvider, agent, open])


    const loadProviders = async () => {
        const { fetchProviders: apiFetch } = await import("@/lib/api")
        const data = await apiFetch()
        setProviders(data)
    }

    const loadOutputModes = async () => {
        const { fetchOutputModes } = await import("@/lib/api")
        const data = await fetchOutputModes()
        setOutputModes(data)
    }

    const handleSave = async () => {
        if (!currentAgentId) return
        setIsSaving(true)
        try {
            const updates = {
                name,
                system_prompt: prompt,
                provider_id: providerId || undefined,
                model_name: model || undefined,
                persona_mode: personaMode
            }
            console.log('[DEBUG] 准备更新 Agent:', currentAgentId, 'updates:', updates)
            await updateAgent(currentAgentId, updates)
            console.log('[DEBUG] Agent 更新成功')
            onOpenChange(false)
        } catch (error) {
            console.error('[ERROR] Agent 更新失败:', error)
        } finally {
            setIsSaving(false)
        }
    }


    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="w-[95vw] max-w-3xl">
                <DialogHeader>
                    <DialogTitle>{t.title}</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="name" className="text-right">
                            {translations[language].agentModal.name}
                        </Label>
                        <Input
                            id="name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="col-span-3"
                        />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="prompt" className="text-right">
                            Prompt
                        </Label>
                        <Textarea
                            id="prompt"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            className="col-span-3 h-32"
                            placeholder="System Prompt..."
                        />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label className="text-right">{translations[language].agentModal.provider}</Label>
                        <Select value={providerId} onValueChange={setProviderId}>
                            <SelectTrigger className="col-span-3">
                                <SelectValue placeholder="Select Provider" />
                            </SelectTrigger>
                            <SelectContent>
                                {providers.map(p => (
                                    <SelectItem key={p.id} value={p.id}>{p.name} ({p.type})</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label className="text-right">输出模式</Label>
                        <Select value={personaMode} onValueChange={setPersonaMode}>
                            <SelectTrigger className="col-span-3">
                                <SelectValue placeholder="选择输出模式" />
                            </SelectTrigger>
                            <SelectContent>
                                {outputModes.map(mode => (
                                    <SelectItem key={mode.id} value={mode.id}>
                                        <div className="flex flex-col">
                                            <span className="font-medium">{mode.name}</span>
                                            {mode.description && (
                                                <span className="text-xs text-gray-500">{mode.description}</span>
                                            )}
                                        </div>
                                    </SelectItem>
                                ))}
                                {outputModes.length === 0 && (
                                    <SelectItem value="normal">普通模式</SelectItem>
                                )}
                            </SelectContent>
                        </Select>
                    </div>
                </div>
                <DialogFooter>
                    <Button onClick={handleSave} disabled={isSaving}>
                        {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {isSaving ? t.updating : t.update}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
