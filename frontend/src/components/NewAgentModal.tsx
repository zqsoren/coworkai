import { useState } from "react"
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

    const { createAgent } = useStore()

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
                        <Label htmlFor="provider" className="text-right">
                            Provider
                        </Label>
                        <Select value={providerId} onValueChange={setProviderId}>
                            <SelectTrigger className="col-span-3">
                                <SelectValue placeholder="Select Provider" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="openai">OpenAI</SelectItem>
                                <SelectItem value="gemini">Gemini</SelectItem>
                                <SelectItem value="anthropic">Anthropic</SelectItem>
                                <SelectItem value="ollama">Ollama</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="model" className="text-right">
                            Model
                        </Label>
                        <Input
                            id="model"
                            value={modelName}
                            onChange={(e) => setModelName(e.target.value)}
                            className="col-span-3"
                            placeholder="e.g. gpt-4o"
                        />
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
