
import React, { useState } from 'react';
import {
    ChevronRight,
    ChevronDown,
    Folder,
    FileText,
    Lock,
    Unlock,
    MoreVertical,
    Trash2,
    FolderPlus,
    File as FileIcon,
    Edit, // Import Edit icon for Rename
    GripVertical
} from 'lucide-react';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import {
    ContextMenu,
    ContextMenuContent,
    ContextMenuItem,
    ContextMenuTrigger,
} from "@/components/ui/context-menu"

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
// FIX: Use import type to avoid runtime error
import type { FileNode } from '@/lib/api';

// DnD Imports
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragOverlay,
} from '@dnd-kit/core';
import type { DragStartEvent, DragEndEvent } from '@dnd-kit/core';
import {
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
    useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface FileTreeProps {
    nodes: FileNode[];
    onSelect: (node: FileNode) => void;
    onToggleLock: (path: string, currentLocked: boolean) => Promise<void>;
    level?: number;
    rootPath?: string;
    onCreateFolder: (parentPath: string) => void;
    onRename: (node: FileNode) => void;
    onDelete: (path: string) => Promise<void>;
    onMove?: (sourcePath: string, targetFolder: string) => Promise<void>;
}

interface FileTreeNodeProps {
    node: FileNode;
    level: number;
    onSelect: (node: FileNode) => void;
    onToggleLock: (path: string, currentLocked: boolean) => Promise<void>;
    onCreateFolder: (parentPath: string) => void;
    onRename: (node: FileNode) => void;
    onDelete: (path: string) => Promise<void>;
    onMove?: (sourcePath: string, targetFolder: string) => Promise<void>;
}

const FileTreeNode: React.FC<FileTreeNodeProps> = ({
    node,
    level,
    onSelect,
    onToggleLock,
    onCreateFolder,
    onRename,
    onDelete,
    onMove
}) => {
    const [expanded, setExpanded] = useState(false);
    const [isHovered, setIsHovered] = useState(false);

    // Draggable & Droppable
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
        isOver
    } = useSortable({
        id: node.path,
        data: {
            type: node.is_dir ? 'FOLDER' : 'FILE',
            node: node
        }
    });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    const handleExpandCallback = (e: React.MouseEvent) => {
        e.stopPropagation();
        setExpanded(!expanded);
    };

    const handleSelectCallback = () => {
        if (node.is_dir) {
            setExpanded(!expanded);
        } else {
            onSelect(node);
        }
    };

    const indent = level * 12;

    return (
        <div ref={setNodeRef} style={style}>
            <ContextMenu>
                <ContextMenuTrigger>
                    <div
                        className={cn(
                            "flex items-center py-1 px-2 rounded-md cursor-pointer hover:bg-muted/50 group text-sm relative transition-colors",
                            isOver && node.is_dir && "bg-blue-100 dark:bg-blue-900/30 ring-1 ring-blue-500", // Highlight drop target
                            // active state if needed
                        )}
                        style={{ paddingLeft: `${indent + 8}px` }}
                        onClick={handleSelectCallback}
                        onMouseEnter={() => setIsHovered(true)}
                        onMouseLeave={() => setIsHovered(false)}

                        // Native HTML5 Drag for external areas (like Chat)
                        draggable={true}
                        onDragStart={(e) => {
                            e.dataTransfer.setData("application/vnd.agentos.filepath", node.path);
                            e.dataTransfer.setData("application/vnd.agentos.filename", node.name);
                            e.dataTransfer.effectAllowed = "copy";
                        }}
                    >
                        {/* Grip Icon for Internal Move */}
                        <div
                            className="absolute left-1 w-4 h-4 flex flex-col items-center justify-center shrink-0 opacity-0 group-hover:opacity-100 cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground transition-opacity"
                            {...attributes}
                            {...listeners}
                        >
                            <GripVertical className="h-4 w-4" />
                        </div>

                        {/* Chevron */}
                        {node.is_dir ? (
                            <div
                                role="button"
                                className="mr-1 p-0.5 rounded-sm hover:bg-muted-foreground/10 z-10 relative" // Ensure click works over drag listener
                                onPointerDown={(e) => e.stopPropagation()} // Prevent drag start on chevron
                                onClick={handleExpandCallback}
                            >
                                {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                            </div>
                        ) : (
                            <span className="w-4 mr-1" /> // Spacer
                        )}

                        {/* Type Icon */}
                        {node.is_dir ? (
                            <Folder className={cn("h-4 w-4 mr-2 text-blue-400 fill-blue-400/20", isOver && "fill-blue-400/50")} />
                        ) : (
                            node.locked ? (
                                <div className="relative mr-2">
                                    <FileIcon className="h-4 w-4 text-orange-400" />
                                    <Lock className="h-2 w-2 absolute -bottom-0.5 -right-0.5 text-orange-600 bg-background rounded-full" />
                                </div>
                            ) : (
                                <FileText className="h-4 w-4 mr-2 text-muted-foreground" />
                            )
                        )}

                        {/* Name */}
                        <span className="truncate flex-1">{node.name}</span>

                        {/* Actions (Hover) */}
                        <div
                            className={cn("flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity", isHovered ? "opacity-100" : "")}
                            onClick={(e) => e.stopPropagation()}
                            onPointerDown={(e) => e.stopPropagation()} // Prevent drag
                        >
                            {/* Lock Toggle (Files only) */}
                            {!node.is_dir && (
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-6 w-6 text-muted-foreground hover:text-foreground"
                                    onClick={(e) => { e.stopPropagation(); onToggleLock(node.path, node.locked); }}
                                    title={node.locked ? "Unlock" : "Lock (Read-Only)"}
                                >
                                    {node.locked ? <Unlock className="h-3 w-3" /> : <Lock className="h-3 w-3" />}
                                </Button>
                            )}

                            {/* More Menu */}
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" size="icon" className="h-6 w-6">
                                        <MoreVertical className="h-3 w-3" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="w-40">
                                    <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onRename(node); }}>
                                        <Edit className="h-3 w-3 mr-2" /> Rename
                                    </DropdownMenuItem>
                                    {node.is_dir && (
                                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onCreateFolder(node.path); }}>
                                            <FolderPlus className="h-3 w-3 mr-2" /> New Folder
                                        </DropdownMenuItem>
                                    )}
                                    <DropdownMenuItem
                                        className="text-red-500 focus:text-red-500"
                                        onClick={(e) => { e.stopPropagation(); onDelete(node.path); }}
                                    >
                                        <Trash2 className="h-3 w-3 mr-2" /> Delete
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>
                    </div>
                </ContextMenuTrigger>
                <ContextMenuContent className="w-40">
                    <ContextMenuItem onClick={() => onRename(node)}>
                        <Edit className="h-3 w-3 mr-2" /> Rename
                    </ContextMenuItem>
                    {node.is_dir && (
                        <ContextMenuItem onClick={() => onCreateFolder(node.path)}>
                            <FolderPlus className="h-3 w-3 mr-2" /> New Folder
                        </ContextMenuItem>
                    )}
                    <ContextMenuItem
                        className="text-red-500 focus:text-red-500"
                        onClick={() => onDelete(node.path)}
                    >
                        <Trash2 className="h-3 w-3 mr-2" /> Delete
                    </ContextMenuItem>
                </ContextMenuContent>
            </ContextMenu>

            {/* Children */}
            {node.is_dir && expanded && node.children && (
                <div className="ml-1 pl-1"> {/* Indentation for children */}
                    {/* We recurse, but notice we don't wrap children in SortableContext here because FileTree does it at the top level */}
                    {/* Actually, SortableContext needs a flat list of IDs for sorting. 
                         For hierarchical trees, Sortable is tricky. 
                         SIMPLIFICATION: We will use Droppable for Folders and Draggable for Files/Folders.
                         We won't use SortableContext for reordering, just for "Moving into".
                     */}
                    <FileTree
                        nodes={node.children}
                        level={level + 1}
                        onSelect={onSelect}
                        onToggleLock={onToggleLock}
                        onCreateFolder={onCreateFolder}
                        onRename={onRename}
                        onDelete={onDelete}
                        onMove={onMove}
                    />
                </div>
            )}
        </div>
    );
};

export const FileTree: React.FC<FileTreeProps> = ({
    nodes,
    level = 0,
    rootPath: _rootPath, // captured but currently unused in recursion, useful if we needed absolute paths
    onSelect,
    onToggleLock,
    onCreateFolder,
    onRename,
    onDelete,
    onMove
}) => {

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8, // Require 8px movement before drag starts (prevents accidental drags on click)
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const [activeId, setActiveId] = useState<string | null>(null);

    const handleDragStart = (event: DragStartEvent) => {
        setActiveId(event.active.id as string);
    };

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;
        setActiveId(null);

        if (!over) return;

        // Active: The item being dragged (path)
        // Over: The target folder (path)

        const sourcePath = active.id as string;
        const targetPath = over.id as string;

        // Check if target is a folder
        const targetNode = over.data.current?.node as FileNode;

        if (sourcePath !== targetPath && onMove) {
            // Logic: If dropped onto a folder, move inside.
            // If dropped onto a file ... maybe do nothing or move to parent? 
            // Let's strictly support "Drop into Folder".

            if (targetNode && targetNode.is_dir) {
                onMove(sourcePath, targetPath);
            }
        }
    };

    // If it's a recursive call (level > 0), we just render the nodes properties.
    // The DndContext should only be at the very top root.

    if (level === 0) {
        return (
            <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
            >
                <div className="select-none">
                    <SortableContext
                        items={nodes.map(n => n.path)}
                        strategy={verticalListSortingStrategy}
                    >
                        {nodes.map((node) => (
                            <FileTreeNode
                                key={node.path}
                                node={node}
                                level={level}
                                onSelect={onSelect}
                                onToggleLock={onToggleLock}
                                onCreateFolder={onCreateFolder}
                                onRename={onRename}
                                onDelete={onDelete}
                                onMove={onMove}
                            />
                        ))}
                    </SortableContext>
                </div>
                {/* Drag Overlay for smooth visuals */}
                <DragOverlay>
                    {activeId ? (
                        <div className="bg-background border rounded px-2 py-1 shadow-lg opacity-80 flex items-center">
                            <span className="text-sm">Moving...</span>
                        </div>
                    ) : null}
                </DragOverlay>
            </DndContext>
        );
    }

    // Recursive rendering (without DndContext)
    return (
        <div className="select-none">
            <SortableContext
                items={nodes.map(n => n.path)}
                strategy={verticalListSortingStrategy}
            >
                {nodes.map((node) => (
                    <FileTreeNode
                        key={node.path}
                        node={node}
                        level={level}
                        onSelect={onSelect}
                        onToggleLock={onToggleLock}
                        onCreateFolder={onCreateFolder}
                        onRename={onRename}
                        onDelete={onDelete}
                        onMove={onMove}
                    />
                ))}
            </SortableContext>
        </div>
    );
};
