import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useStore } from "@/store"
import { Plus } from "lucide-react"

export function NewAgentModal() {
    const [open, setOpen] = useState(false)
    const [isLoading, setIsLoading] = useState(false)

    const [name, setName] = useState("")
    const [systemPrompt, setSystemPrompt] = useState("")
    const [providerId, setProviderId] = useState("builtin_glm4air_free")
    const [modelName, setModelName] = useState("z-ai/glm-4.5-air:free")
    const [providers, setProviders] = useState<any[]>([])

    const { createAgent } = useStore()

    // Load providers when modal opens
    useEffect(() => {
        if (open) {
            loadProviders()
        }
    }, [open])

    // Auto-sync model when provider changes
    useEffect(() => {
        const selected = providers.find(p => p.id === providerId)
        if (selected) {
            setModelName(selected.models?.[0] || "")
        }
    }, [providerId, providers])

    const loadProviders = async () => {
        const { fetchProviders: apiFetch } = await import("@/lib/api")
        const data = await apiFetch()
        setProviders(data)
        // Default to GLM 4.5 Air if available
        if (data.length > 0) {
            const defaultP = data.find((p: any) => p.id === "builtin_glm4air_free")
            if (defaultP) {
                setProviderId(defaultP.id)
                setModelName(defaultP.models?.[0] || "")
            }
        }
    }

    const handleCreate = async () => {
        if (!name.trim()) return
        setIsLoading(true)
        try {
            await createAgent(name, systemPrompt, providerId, modelName)
            setOpen(false)
            setName("")
            setSystemPrompt("")
        } catch (error) {
            console.error("Failed to create agent:", error)
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="ghost" className="w-full justify-start px-3 py-2 text-sm font-normal text-gray-600 hover:shadow-[inset_2px_2px_5px_rgb(163,177,198,0.6),inset_-2px_-2px_5px_rgba(255,255,255,0.5)] rounded-xl transition-shadow duration-300 mt-1 gap-3 hover:bg-transparent opacity-60 hover:opacity-100">
                    <Plus className="w-4 h-4 shrink-0" /> <span className="truncate">New Agent</span>
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Create New Agent</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="name" className="text-right">
                            Name
                        </Label>
                        <Input
                            id="name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="col-span-3"
                            placeholder="e.g. Code Reviewer"
                        />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="systemPrompt" className="text-right">
                            System Prompt
                        </Label>
                        <Textarea
                            id="systemPrompt"
                            value={systemPrompt}
                            onChange={(e) => setSystemPrompt(e.target.value)}
                            className="col-span-3 h-24"
                            placeholder="Enter system prompt (defines behavior and role)..."
                        />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label className="text-right">LLM Provider</Label>
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
                </div>
                <DialogFooter>
                    <Button onClick={handleCreate} disabled={isLoading}>
                        {isLoading ? "Creating..." : "Create Agent"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
