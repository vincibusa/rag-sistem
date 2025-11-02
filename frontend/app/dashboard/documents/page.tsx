'use client'

import { useState, useMemo, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from '@/components/ui/table'
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@/components/ui/select'
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { FileText, Download, Search, Filter, MoreVertical, Eye, Trash2, RefreshCw, Sparkles, Upload, ChevronLeft, ChevronRight } from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import {
	listDocuments,
	downloadDocument,
	deleteDocument,
	reprocessDocument,
	ApiClientError,
} from '@/lib/api-client'
import type { DocumentSummary } from '@/lib/types'

export default function DocumentsPage() {
	const [searchQuery, setSearchQuery] = useState('')
	const [filterType, setFilterType] = useState<string>('all')
	const [filterStatus, setFilterStatus] = useState<string>('all')
	const [isLoading, setIsLoading] = useState(false)
	const [documents, setDocuments] = useState<DocumentSummary[]>([])
	const [total, setTotal] = useState(0)
	const [limit] = useState(20)
	const [offset, setOffset] = useState(0)
	const [actionState, setActionState] = useState<Record<string, 'delete' | 'reprocess'>>({})

	const fetchDocuments = useCallback(async () => {
		setIsLoading(true)
		try {
			const response = await listDocuments(limit, offset)
			setDocuments(response.items)
			setTotal(response.total)
		} catch (error) {
			const errorMessage =
				error instanceof ApiClientError
					? error.detail
					: 'Errore nel caricamento dei documenti'
			toast.error('Errore nel caricamento', {
				description: errorMessage,
			})
		} finally {
			setIsLoading(false)
		}
	}, [limit, offset])

	useEffect(() => {
		fetchDocuments()
	}, [fetchDocuments])

	const getFileTypeFromMime = (contentType: string): string => {
		if (contentType.includes('pdf')) return 'PDF'
		if (contentType.includes('wordprocessingml')) return 'Word'
		if (contentType.includes('msword')) return 'Word'
		if (contentType.includes('spreadsheetml')) return 'Excel'
		if (contentType.includes('ms-excel')) return 'Excel'
		if (contentType.includes('text/plain')) return 'Text'
		return 'Unknown'
	}

	const mapStatus = (status: DocumentSummary['status']): 'processing' | 'ready' | 'error' => {
		switch (status) {
			case 'ready':
				return 'ready'
			case 'failed':
				return 'error'
			case 'processing':
			case 'new':
			default:
				return 'processing'
		}
	}

	const filteredDocuments = useMemo(() => {
		return documents.filter((doc) => {
			const matchesSearch = doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
			const docType = getFileTypeFromMime(doc.content_type)
			const matchesType = filterType === 'all' || docType === filterType
			const mappedStatus = mapStatus(doc.status)
			const matchesStatus = filterStatus === 'all' || mappedStatus === filterStatus
			return matchesSearch && matchesType && matchesStatus
		})
	}, [documents, searchQuery, filterType, filterStatus])

	const formatFileSize = (bytes: number): string => {
		if (bytes < 1024) return `${bytes} B`
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
	}

	const formatDate = (dateString: string): string => {
		return new Date(dateString).toLocaleDateString('it-IT', {
			day: '2-digit',
			month: '2-digit',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
		})
	}

	const getStatusBadge = (status: 'processing' | 'ready' | 'error') => {
		switch (status) {
			case 'processing':
				return <Badge variant="secondary">Elaborazione</Badge>
			case 'ready':
				return <Badge variant="default" className="bg-green-600">Pronto</Badge>
			case 'error':
				return <Badge variant="destructive">Errore</Badge>
			default:
				return null
		}
	}

	const handleDownload = async (documentId: string, documentName: string) => {
		try {
			const blob = await downloadDocument(documentId)
			const url = window.URL.createObjectURL(blob)
			const a = document.createElement('a')
			a.href = url
			a.download = documentName
			document.body.appendChild(a)
			a.click()
			window.URL.revokeObjectURL(url)
			document.body.removeChild(a)
			toast.success(`Download completato: ${documentName}`)
		} catch (error) {
			const errorMessage =
				error instanceof ApiClientError
					? error.detail
					: 'Errore durante il download'
			toast.error('Errore download', {
				description: errorMessage,
			})
		}
	}

	const handleView = (documentId: string) => {
		const doc = documents.find((d) => d.id === documentId)
		if (!doc) return

		if (doc.content_type.includes('pdf')) {
			// For PDF, download and open in new tab
			handleDownload(documentId, doc.filename).then(() => {
				// Open in new tab if possible
				toast.info('Apri il file scaricato per visualizzarlo')
			})
		} else {
			toast.info('Download il file per visualizzarlo', {
				description: 'Alcuni formati richiedono l\'applicazione locale',
			})
		}
	}

	const handleDelete = async (documentId: string, documentName: string) => {
		const confirmed = window.confirm(
			`Sei sicuro di voler eliminare "${documentName}"? L'operazione non può essere annullata.`
		)
		if (!confirmed) return

		setActionState((prev) => ({ ...prev, [documentId]: 'delete' }))

		try {
			await deleteDocument(documentId)
			toast.success('Documento eliminato', {
				description: documentName,
			})

			const isLastItemOnPage = documents.length === 1
			if (isLastItemOnPage && offset > 0) {
				setOffset((prev) => Math.max(0, prev - limit))
			} else {
				await fetchDocuments()
			}
		} catch (error) {
			const errorMessage =
				error instanceof ApiClientError
					? error.detail
					: 'Errore durante l\'eliminazione'
			toast.error('Errore eliminazione', {
				description: errorMessage,
			})
		} finally {
			setActionState((prev) => {
				const next = { ...prev }
				delete next[documentId]
				return next
			})
		}
	}

	const handleReprocess = async (documentId: string) => {
		setActionState((prev) => ({ ...prev, [documentId]: 'reprocess' }))
		try {
			const updatedDocument = await reprocessDocument(documentId)
			setDocuments((prev) =>
				prev.map((doc) => (doc.id === documentId ? updatedDocument : doc))
			)
			toast.success('Rielaborazione avviata', {
				description: 'Il documento verrà elaborato nuovamente a breve.',
			})
		} catch (error) {
			const errorMessage =
				error instanceof ApiClientError
					? error.detail
					: 'Errore durante la rielaborazione'
			toast.error('Errore rielaborazione', {
				description: errorMessage,
			})
		} finally {
			setActionState((prev) => {
				const next = { ...prev }
				delete next[documentId]
				return next
			})
		}
	}

	const handleRefresh = () => {
		fetchDocuments()
		toast.success('Lista documenti aggiornata')
	}

	const handlePreviousPage = () => {
		if (offset > 0) {
			setOffset((prev) => Math.max(0, prev - limit))
		}
	}

	const handleNextPage = () => {
		if (offset + limit < total) {
			setOffset((prev) => prev + limit)
		}
	}

	const getFileIcon = (contentType: string) => {
		const type = getFileTypeFromMime(contentType)
		switch (type) {
			case 'PDF':
				return '📄'
			case 'Word':
				return '📝'
			case 'Excel':
				return '📊'
			case 'Text':
				return '📃'
			default:
				return '📄'
		}
	}

	return (
		<div className="space-y-4 md:space-y-6">
			<div>
				<h2 className="text-2xl md:text-3xl font-bold tracking-tight flex items-center gap-2">
					<Sparkles className="h-6 w-6 text-primary" />
					Documenti
				</h2>
				<p className="text-sm md:text-base text-muted-foreground mt-1">
					Gestisci e visualizza i tuoi documenti caricati
				</p>
			</div>

			<Card>
				<CardHeader>
					<div className="flex items-center justify-between">
						<div>
							<CardTitle className="flex items-center gap-2">
								<FileText className="h-5 w-5 text-primary" />
								Lista Documenti
							</CardTitle>
							<CardDescription className="mt-1">
								{filteredDocuments.length} documento{filteredDocuments.length !== 1 ? 'i' : ''} trovato
								{filteredDocuments.length !== total && ` su ${total}`}
							</CardDescription>
						</div>
						<div className="flex items-center gap-2">
							<Button
								variant="outline"
								size="sm"
								onClick={handleRefresh}
								disabled={isLoading}
								aria-label="Aggiorna lista"
							>
								<RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
							</Button>
							<Button asChild size="sm">
								<Link href="/dashboard/upload" className="flex items-center gap-2">
									<Upload className="h-4 w-4" />
									<span className="hidden sm:inline">Carica Documento</span>
									<span className="sm:hidden">Carica</span>
								</Link>
							</Button>
						</div>
					</div>
				</CardHeader>
				<CardContent>
					{/* Filtri e ricerca - mobile first */}
					<div className="space-y-3 mb-6">
						<div className="relative">
							<Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground z-10" />
							<Input
								placeholder="Cerca documenti..."
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.target.value)}
								className="pl-9"
								aria-label="Cerca documenti"
							/>
						</div>
						<div className="flex flex-col sm:flex-row gap-2">
							<Select value={filterType} onValueChange={setFilterType}>
								<SelectTrigger className="w-full sm:w-[150px]">
									<Filter className="h-4 w-4 mr-2" />
									<SelectValue placeholder="Tipo" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="all">Tutti i tipi</SelectItem>
									<SelectItem value="PDF">PDF</SelectItem>
									<SelectItem value="Word">Word</SelectItem>
									<SelectItem value="Excel">Excel</SelectItem>
									<SelectItem value="Text">Text</SelectItem>
								</SelectContent>
							</Select>
							<Select value={filterStatus} onValueChange={setFilterStatus}>
								<SelectTrigger className="w-full sm:w-[150px]">
									<SelectValue placeholder="Stato" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="all">Tutti gli stati</SelectItem>
									<SelectItem value="processing">Elaborazione</SelectItem>
									<SelectItem value="ready">Pronto</SelectItem>
									<SelectItem value="error">Errore</SelectItem>
								</SelectContent>
							</Select>
						</div>
					</div>

					{isLoading ? (
						<div className="space-y-3">
							{Array.from({ length: 3 }).map((_, i) => (
								<div key={i} className="flex items-center gap-4 p-4 border rounded-lg">
									<Skeleton className="h-10 w-10 rounded-lg" />
									<div className="flex-1 space-y-2">
										<Skeleton className="h-4 w-3/4" />
										<Skeleton className="h-3 w-1/2" />
									</div>
									<Skeleton className="h-8 w-8 rounded" />
								</div>
							))}
						</div>
					) : filteredDocuments.length === 0 ? (
						<div className="text-center py-16">
							<div className="relative inline-block mb-6">
								<div className="rounded-full bg-primary/10 p-6">
									<FileText className="h-12 w-12 text-primary" />
								</div>
							</div>
							<h3 className="text-lg font-semibold mb-2">
								{documents.length === 0
									? 'Nessun documento caricato'
									: 'Nessun documento corrisponde ai filtri'}
							</h3>
							<p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
								{documents.length === 0
									? 'Inizia caricando il tuo primo documento per iniziare a utilizzare il sistema RAG.'
									: 'Prova a modificare i filtri di ricerca per trovare i documenti.'}
							</p>
							{documents.length === 0 && (
								<Button asChild size="lg">
									<Link href="/dashboard/upload" className="flex items-center gap-2">
										<Upload className="h-4 w-4" />
										Carica il primo documento
									</Link>
								</Button>
							)}
						</div>
					) : (
						<div className="overflow-x-auto">
							<Table>
								<TableHeader>
									<TableRow className="hover:bg-transparent">
										<TableHead className="w-[40%]">Nome</TableHead>
										<TableHead className="hidden sm:table-cell">Tipo</TableHead>
										<TableHead className="hidden md:table-cell">Dimensione</TableHead>
										<TableHead className="hidden lg:table-cell">Data</TableHead>
										<TableHead>Stato</TableHead>
										<TableHead className="text-right">Azioni</TableHead>
									</TableRow>
								</TableHeader>
								<TableBody>
						{filteredDocuments.map((doc) => {
							const docType = getFileTypeFromMime(doc.content_type)
							const mappedStatus = mapStatus(doc.status)
							const currentAction = actionState[doc.id]
							const isReprocessing = currentAction === 'reprocess'
							const isDeleting = currentAction === 'delete'
							return (
								<TableRow
												key={doc.id}
												className="hover:bg-muted/50"
											>
												<TableCell className="font-medium">
													<div className="flex items-center gap-3">
														<div className="text-2xl flex-shrink-0">
															{getFileIcon(doc.content_type)}
														</div>
														<div className="flex-1 min-w-0">
															<p className="truncate font-medium">{doc.filename}</p>
															<div className="text-xs text-muted-foreground mt-1 sm:hidden flex items-center gap-2">
																<span>{docType}</span>
																<span>•</span>
																<span>{formatFileSize(doc.size_bytes)}</span>
															</div>
														</div>
													</div>
												</TableCell>
												<TableCell className="hidden sm:table-cell">
													<Badge variant="outline">{docType}</Badge>
												</TableCell>
												<TableCell className="hidden md:table-cell text-muted-foreground">
													{formatFileSize(doc.size_bytes)}
												</TableCell>
												<TableCell className="hidden lg:table-cell text-muted-foreground text-sm">
													{formatDate(doc.created_at)}
												</TableCell>
												<TableCell>{getStatusBadge(mappedStatus)}</TableCell>
												<TableCell className="text-right">
													<div className="flex items-center justify-end gap-1">
														<Button
															variant="ghost"
															size="icon"
															onClick={() => handleDownload(doc.id, doc.filename)}
															className="h-8 w-8"
															aria-label="Scarica documento"
														>
															<Download className="h-4 w-4" />
														</Button>
										<DropdownMenu>
											<DropdownMenuTrigger asChild>
												<Button
													variant="ghost"
													size="icon"
													className="h-8 w-8"
													aria-label="Altre opzioni"
												>
													<MoreVertical className="h-4 w-4" />
												</Button>
											</DropdownMenuTrigger>
											<DropdownMenuContent align="end">
												<DropdownMenuItem onClick={() => handleView(doc.id)}>
													<Eye className="h-4 w-4 mr-2" />
													Visualizza
												</DropdownMenuItem>
												<DropdownMenuItem onClick={() => handleDownload(doc.id, doc.filename)}>
													<Download className="h-4 w-4 mr-2" />
													Scarica
												</DropdownMenuItem>
												{mappedStatus === 'error' && (
													<DropdownMenuItem
														onClick={() => handleReprocess(doc.id)}
														disabled={isReprocessing}
													>
														<RefreshCw
															className={cn('h-4 w-4 mr-2', isReprocessing && 'animate-spin')}
														/>
														Rielabora
													</DropdownMenuItem>
												)}
												<DropdownMenuSeparator />
												<DropdownMenuItem
													onClick={() => handleDelete(doc.id, doc.filename)}
													disabled={isDeleting || isReprocessing}
													className="text-destructive focus:text-destructive"
												>
													<Trash2
														className={cn('h-4 w-4 mr-2', isDeleting && 'animate-spin')}
													/>
													Elimina
												</DropdownMenuItem>
											</DropdownMenuContent>
										</DropdownMenu>
													</div>
												</TableCell>
											</TableRow>
										)
									})}
								</TableBody>
							</Table>
						</div>
					)}

					{/* Pagination */}
					{total > limit && (
						<div className="flex items-center justify-between mt-4 pt-4 border-t">
							<div className="text-sm text-muted-foreground">
								Mostrando {offset + 1}-{Math.min(offset + limit, total)} di {total} documenti
							</div>
							<div className="flex items-center gap-2">
								<Button
									variant="outline"
									size="sm"
									onClick={handlePreviousPage}
									disabled={offset === 0 || isLoading}
									aria-label="Pagina precedente"
								>
									<ChevronLeft className="h-4 w-4 mr-1" />
									Precedente
								</Button>
								<Button
									variant="outline"
									size="sm"
									onClick={handleNextPage}
									disabled={offset + limit >= total || isLoading}
									aria-label="Pagina successiva"
								>
									Successiva
									<ChevronRight className="h-4 w-4 ml-1" />
								</Button>
							</div>
						</div>
					)}
				</CardContent>
			</Card>
		</div>
	)
}
