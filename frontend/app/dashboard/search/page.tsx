'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Skeleton } from '@/components/ui/skeleton'
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { MessageSquare, Send, Copy, Check, Loader2, User, Bot, MoreVertical, RefreshCw, Trash2, Edit2, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { toast } from 'sonner'
import { ragSearch, ApiClientError } from '@/lib/api-client'

interface Message {
	id: string
	role: 'user' | 'assistant'
	content: string
	timestamp: Date
}

const SUGGESTED_QUESTIONS = [
	'Quali sono i punti principali del documento?',
	'Riassumi il contenuto',
	'Ci sono riferimenti a date importanti?',
	'Quali sono le conclusioni?',
]

export default function ChatPage() {
	const [messages, setMessages] = useState<Message[]>([])
	const [input, setInput] = useState('')
	const [isLoading, setIsLoading] = useState(false)
	const [copiedId, setCopiedId] = useState<string | null>(null)
	const [streamingContent, setStreamingContent] = useState<string>('')
	const scrollAreaRef = useRef<HTMLDivElement>(null)
	const textareaRef = useRef<HTMLTextAreaElement>(null)
	const messagesEndRef = useRef<HTMLDivElement>(null)

	// Auto-scroll to bottom when new messages arrive
	const scrollToBottom = useCallback(() => {
		if (scrollAreaRef.current) {
			const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
			if (scrollContainer) {
				scrollContainer.scrollTo({
					top: scrollContainer.scrollHeight,
					behavior: 'auto',
				})
			}
		}
	}, [])

	useEffect(() => {
		scrollToBottom()
	}, [messages, isLoading, streamingContent, scrollToBottom])

	// Auto-resize textarea
	useEffect(() => {
		const textarea = textareaRef.current
		if (textarea) {
			textarea.style.height = 'auto'
			textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
		}
	}, [input])

	// Focus textarea on mount
	useEffect(() => {
		textareaRef.current?.focus()
	}, [])

	const handleSend = async (messageContent?: string) => {
		const content = messageContent || input.trim()
		if (!content || isLoading) return

		const userMessage: Message = {
			id: Date.now().toString(),
			role: 'user',
			content,
			timestamp: new Date(),
		}

		setMessages((prev) => [...prev, userMessage])
		if (!messageContent) setInput('')
		setIsLoading(true)
		setStreamingContent('')

		try {
			const response = await ragSearch({
				query: content,
				top_k: 5,
			})

			// Build response text with answer and context
			let responseText = ''

			if (response.answer) {
				responseText = response.answer
			} else {
				responseText = 'Ho trovato alcune informazioni nei tuoi documenti:\n\n'
			}

			// Add chunks as context if available
			if (response.chunks && response.chunks.length > 0) {
				responseText += '\n\n**Fonti trovate:**\n\n'
				response.chunks.forEach((chunk, index) => {
					responseText += `${index + 1}. ${chunk.text.substring(0, 200)}...\n`
					if (chunk.score !== null && chunk.score !== undefined) {
						responseText += `   _Rilevanza: ${(chunk.score * 100).toFixed(1)}%_\n\n`
					}
				})
			}

			// Simulate streaming for better UX
			const chars = responseText.split('')
			let currentText = ''
			for (let i = 0; i < chars.length; i++) {
				currentText += chars[i]
				setStreamingContent(currentText)
				await new Promise((resolve) => setTimeout(resolve, 10))
			}

			const assistantMessage: Message = {
				id: (Date.now() + 1).toString(),
				role: 'assistant',
				content: responseText,
				timestamp: new Date(),
			}

			setMessages((prev) => [...prev, assistantMessage])
			setStreamingContent('')
			setIsLoading(false)
		} catch (error) {
			const errorMessage =
				error instanceof ApiClientError
					? error.detail
					: 'Errore durante la ricerca. Riprova più tardi.'
			toast.error('Errore durante la ricerca', {
				description: errorMessage,
			})

			const errorResponse: Message = {
				id: (Date.now() + 1).toString(),
				role: 'assistant',
				content: `Mi dispiace, si è verificato un errore: ${errorMessage}`,
				timestamp: new Date(),
			}

			setMessages((prev) => [...prev, errorResponse])
			setStreamingContent('')
			setIsLoading(false)
		}
	}

	const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
		if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
			e.preventDefault()
			handleSend()
		}
	}

	const handleCopy = async (messageId: string, content: string) => {
		try {
			await navigator.clipboard.writeText(content)
			setCopiedId(messageId)
			toast.success('Messaggio copiato')
			setTimeout(() => setCopiedId(null), 2000)
		} catch {
			toast.error('Errore durante la copia')
		}
	}

	const handleDelete = (messageId: string) => {
		setMessages((prev) => prev.filter((m) => m.id !== messageId))
		toast.success('Messaggio eliminato')
	}

	const handleRegenerate = (messageId: string) => {
		const messageIndex = messages.findIndex((m) => m.id === messageId)
		if (messageIndex > 0 && messages[messageIndex - 1].role === 'user') {
			const userMessage = messages[messageIndex - 1].content
			setMessages((prev) => prev.slice(0, messageIndex))
			handleSend(userMessage)
		}
	}

	const handleSuggestionClick = (suggestion: string) => {
		setInput(suggestion)
		textareaRef.current?.focus()
	}

	return (
		<>
			<div className="flex h-[calc(100vh-8rem)] sm:h-[calc(100vh-9rem)] flex-col relative">
				{/* Header with better styling */}
				<div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 py-3 flex-shrink-0 sticky top-0 z-10">
					<div className="flex items-center justify-between">
						<div>
							<h2 className="text-lg sm:text-xl font-semibold flex items-center gap-2">
								<Sparkles className="h-5 w-5 text-primary" />
								Chat AI
							</h2>
							<p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
								Chat intelligente basata sui tuoi documenti con RAG
							</p>
						</div>
					</div>
				</div>

				{/* Messages Area */}
				<ScrollArea ref={scrollAreaRef} className="flex-1 relative">
					<div className="max-w-3xl mx-auto py-6 px-4 space-y-6">
						{messages.length === 0 ? (
							<div className="flex flex-col items-center justify-center min-h-[400px] text-center px-4">
								<div className="relative mb-6">
									<div className="rounded-full bg-primary/10 p-5">
										<MessageSquare className="h-10 w-10 text-primary" />
									</div>
								</div>
								<h3 className="text-xl font-semibold mb-2">
									Inizia una conversazione
								</h3>
								<p className="text-sm text-muted-foreground max-w-md mb-6">
									Fai domande sui tuoi documenti caricati. Il sistema RAG ti fornirà
									risposte basate sul contesto dei documenti.
								</p>
								{/* Suggested Questions */}
								<div className="w-full max-w-md space-y-2">
									<p className="text-xs text-muted-foreground font-medium mb-2">
										Suggerimenti:
									</p>
									{SUGGESTED_QUESTIONS.map((question, index) => (
										<Button
											key={index}
											variant="outline"
											className="w-full text-left justify-start text-sm h-auto py-2.5 px-3"
											onClick={() => handleSuggestionClick(question)}
										>
											<span className="truncate">{question}</span>
										</Button>
									))}
								</div>
							</div>
						) : (
							messages.map((message) => (
								<div
									key={message.id}
									className={cn(
										'flex gap-3 sm:gap-4 group',
										message.role === 'user' ? 'justify-end' : 'justify-start'
									)}
								>
									{message.role === 'assistant' && (
										<Avatar className="h-8 w-8 sm:h-9 sm:w-9 flex-shrink-0 mt-1 ring-2 ring-primary/10">
											<AvatarFallback className="bg-primary/10 text-primary">
												<Bot className="h-4 w-4 sm:h-5 sm:w-5" />
											</AvatarFallback>
										</Avatar>
									)}

									<div
										className={cn(
											'flex flex-col gap-2 max-w-[85%] sm:max-w-[75%]',
											message.role === 'user' ? 'items-end' : 'items-start'
										)}
									>
										<div
											className={cn(
												'rounded-2xl px-4 py-3 text-sm leading-relaxed break-words shadow-sm',
												message.role === 'user'
													? 'bg-primary text-primary-foreground shadow-primary/20'
													: 'bg-muted text-foreground'
											)}
										>
											{message.role === 'user' ? (
												<div className="whitespace-pre-wrap break-words">{message.content}</div>
											) : (
												<div className="prose prose-sm dark:prose-invert max-w-none prose-headings:font-semibold prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-1 prose-code:text-xs prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:my-2 prose-pre:bg-muted prose-pre:border prose-a:text-primary hover:prose-a:underline prose-strong:font-semibold prose-blockquote:border-l-4 prose-blockquote:border-primary prose-blockquote:pl-4 prose-blockquote:italic">
													<ReactMarkdown remarkPlugins={[remarkGfm]}>
														{message.content}
													</ReactMarkdown>
												</div>
											)}
										</div>

										{message.role === 'assistant' && (
											<div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
												<Button
													variant="ghost"
													size="icon"
													className="h-7 w-7"
													onClick={() => handleCopy(message.id, message.content)}
													title="Copia"
												>
													{copiedId === message.id ? (
														<Check className="h-3.5 w-3.5 text-green-600" />
													) : (
														<Copy className="h-3.5 w-3.5" />
													)}
												</Button>
												<DropdownMenu>
													<DropdownMenuTrigger asChild>
														<Button
															variant="ghost"
															size="icon"
															className="h-7 w-7"
															title="Altre opzioni"
														>
															<MoreVertical className="h-3.5 w-3.5" />
														</Button>
													</DropdownMenuTrigger>
													<DropdownMenuContent align="start">
														<DropdownMenuItem onClick={() => handleRegenerate(message.id)}>
															<RefreshCw className="h-4 w-4 mr-2" />
															Rigenera risposta
														</DropdownMenuItem>
														<DropdownMenuItem onClick={() => handleCopy(message.id, message.content)}>
															<Copy className="h-4 w-4 mr-2" />
															Copia
														</DropdownMenuItem>
														<DropdownMenuItem
															onClick={() => handleDelete(message.id)}
															className="text-destructive"
														>
															<Trash2 className="h-4 w-4 mr-2" />
															Elimina
														</DropdownMenuItem>
													</DropdownMenuContent>
												</DropdownMenu>
											</div>
										)}
									</div>

									{message.role === 'user' && (
										<Avatar className="h-8 w-8 sm:h-9 sm:w-9 flex-shrink-0 mt-1 ring-2 ring-secondary/20">
											<AvatarFallback className="bg-secondary">
												<User className="h-4 w-4 sm:h-5 sm:w-5" />
											</AvatarFallback>
										</Avatar>
									)}
								</div>
							))
						)}

						{/* Streaming message */}
						{isLoading && streamingContent && (
							<div className="flex gap-3 sm:gap-4 justify-start">
								<Avatar className="h-8 w-8 sm:h-9 sm:w-9 flex-shrink-0 mt-1 ring-2 ring-primary/10">
									<AvatarFallback className="bg-primary/10 text-primary">
										<Bot className="h-4 w-4 sm:h-5 sm:w-5" />
									</AvatarFallback>
								</Avatar>
								<div className="flex flex-col gap-2 max-w-[85%] sm:max-w-[75%]">
									<div className="rounded-2xl bg-muted px-4 py-3 text-sm leading-relaxed break-words shadow-sm">
										<div className="prose prose-sm dark:prose-invert max-w-none prose-headings:font-semibold prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-1 prose-code:text-xs prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:my-2 prose-pre:bg-muted prose-pre:border prose-a:text-primary hover:prose-a:underline prose-strong:font-semibold">
											<ReactMarkdown remarkPlugins={[remarkGfm]}>
												{streamingContent}
											</ReactMarkdown>
										</div>
									</div>
								</div>
							</div>
						)}

						{/* Loading skeleton */}
						{isLoading && !streamingContent && (
							<div className="flex gap-3 sm:gap-4 justify-start">
								<Avatar className="h-8 w-8 sm:h-9 sm:w-9 flex-shrink-0 mt-1">
									<AvatarFallback className="bg-primary/10 text-primary">
										<Bot className="h-4 w-4 sm:h-5 sm:w-5" />
									</AvatarFallback>
								</Avatar>
								<div className="flex flex-col gap-2 max-w-[85%] sm:max-w-[75%]">
									<div className="rounded-2xl bg-muted px-4 py-3 space-y-2">
										<Skeleton className="h-4 w-full" />
										<Skeleton className="h-4 w-5/6" />
										<Skeleton className="h-4 w-4/6" />
									</div>
								</div>
							</div>
						)}

						<div ref={messagesEndRef} />
					</div>
				</ScrollArea>

				{/* Input Area - Fixed at bottom with better styling */}
				<div className="border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 py-3 flex-shrink-0 sticky bottom-0 z-10">
					<div className="max-w-3xl mx-auto">
						<div className="flex gap-2 items-end">
							<div className="flex-1 relative">
								<Textarea
									ref={textareaRef}
									placeholder="Fai una domanda sui tuoi documenti..."
									value={input}
									onChange={(e) => setInput(e.target.value)}
									onKeyDown={handleKeyDown}
									disabled={isLoading}
									className="min-h-[52px] max-h-[200px] resize-none pr-12 sm:pr-14"
									rows={1}
									aria-label="Input messaggio"
								/>
								<div className="absolute bottom-2 right-2 text-xs text-muted-foreground hidden sm:flex items-center gap-1">
									<span>Invio</span>
									<span>•</span>
									<span>Shift+Invio nuova riga</span>
								</div>
							</div>
							<Button
								onClick={() => handleSend()}
								disabled={!input.trim() || isLoading}
								size="icon"
								className="h-[52px] w-[52px] flex-shrink-0 disabled:opacity-50"
								aria-label="Invia messaggio"
							>
								{isLoading ? (
									<Loader2 className="h-4 w-4 animate-spin" />
								) : (
									<Send className="h-4 w-4" />
								)}
							</Button>
						</div>
					</div>
				</div>
			</div>
		</>
	)
}
