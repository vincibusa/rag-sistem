'use client'

import { useState, useMemo } from 'react'
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
import { FileText, Download, Search, Filter, MoreVertical, Eye, Trash2, RefreshCw, Sparkles, Upload } from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

interface Document {
	id: string
	name: string
	type: string
	size: number
	uploadedAt: string
	status: 'processing' | 'ready' | 'error'
	chunks?: number
}

// Mock data - sostituire con dati reali
const mockDocuments: Document[] = []

export default function DocumentsPage() {
	const [searchQuery, setSearchQuery] = useState('')
	const [filterType, setFilterType] = useState<string>('all')
	const [filterStatus, setFilterStatus] = useState<string>('all')
	const [isLoading] = useState(false)

	const documents = useMemo(() => {
		return mockDocuments.filter((doc) => {
			const matchesSearch = doc.name.toLowerCase().includes(searchQuery.toLowerCase())
			const matchesType = filterType === 'all' || doc.type === filterType
			const matchesStatus = filterStatus === 'all' || doc.status === filterStatus
			return matchesSearch && matchesType && matchesStatus
		})
	}, [searchQuery, filterType, filterStatus])

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

	const getStatusBadge = (status: Document['status']) => {
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
		// TODO: Implementare download reale
		toast.success(`Download avviato: ${documentName}`)
		console.log('Download document:', documentId)
	}

	const handleView = (documentId: string) => {
		// TODO: Implementare visualizzazione
		toast.info('Apertura documento in corso...')
	}

	const handleDelete = (documentId: string, documentName: string) => {
		// TODO: Implementare eliminazione
		toast.success(`Documento eliminato: ${documentName}`)
	}

	const handleReprocess = (documentId: string) => {
		// TODO: Implementare rielaborazione
		toast.info('Rielaborazione avviata...')
	}

	const getFileIcon = (type: string) => {
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
								{documents.length} documento{documents.length !== 1 ? 'i' : ''} trovato
								{documents.length !== mockDocuments.length && ` su ${mockDocuments.length}`}
							</CardDescription>
						</div>
						<Button asChild size="sm">
							<Link href="/dashboard/upload" className="flex items-center gap-2">
								<Upload className="h-4 w-4" />
								<span className="hidden sm:inline">Carica Documento</span>
								<span className="sm:hidden">Carica</span>
							</Link>
						</Button>
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
					) : documents.length === 0 ? (
						<div className="text-center py-16">
							<div className="relative inline-block mb-6">
								<div className="rounded-full bg-primary/10 p-6">
									<FileText className="h-12 w-12 text-primary" />
								</div>
							</div>
							<h3 className="text-lg font-semibold mb-2">
								{mockDocuments.length === 0
									? 'Nessun documento caricato'
									: 'Nessun documento corrisponde ai filtri'}
							</h3>
							<p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
								{mockDocuments.length === 0
									? 'Inizia caricando il tuo primo documento per iniziare a utilizzare il sistema RAG.'
									: 'Prova a modificare i filtri di ricerca per trovare i documenti.'}
							</p>
							{mockDocuments.length === 0 && (
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
									{documents.map((doc) => (
										<TableRow
											key={doc.id}
											className="hover:bg-muted/50"
										>
											<TableCell className="font-medium">
												<div className="flex items-center gap-3">
													<div className="text-2xl flex-shrink-0">
														{getFileIcon(doc.type)}
													</div>
													<div className="flex-1 min-w-0">
														<p className="truncate font-medium">{doc.name}</p>
														<div className="text-xs text-muted-foreground mt-1 sm:hidden flex items-center gap-2">
															<span>{doc.type}</span>
															<span>•</span>
															<span>{formatFileSize(doc.size)}</span>
														</div>
													</div>
												</div>
											</TableCell>
											<TableCell className="hidden sm:table-cell">
												<Badge variant="outline">{doc.type}</Badge>
											</TableCell>
											<TableCell className="hidden md:table-cell text-muted-foreground">
												{formatFileSize(doc.size)}
											</TableCell>
											<TableCell className="hidden lg:table-cell text-muted-foreground text-sm">
												{formatDate(doc.uploadedAt)}
											</TableCell>
											<TableCell>{getStatusBadge(doc.status)}</TableCell>
											<TableCell className="text-right">
												<div className="flex items-center justify-end gap-1">
													<Button
														variant="ghost"
														size="icon"
														onClick={() => handleDownload(doc.id, doc.name)}
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
															<DropdownMenuItem onClick={() => handleDownload(doc.id, doc.name)}>
																<Download className="h-4 w-4 mr-2" />
																Scarica
															</DropdownMenuItem>
															{doc.status === 'processing' && (
																<DropdownMenuItem onClick={() => handleReprocess(doc.id)}>
																	<RefreshCw className="h-4 w-4 mr-2" />
																	Rielabora
																</DropdownMenuItem>
															)}
															<DropdownMenuSeparator />
															<DropdownMenuItem
																onClick={() => handleDelete(doc.id, doc.name)}
																className="text-destructive focus:text-destructive"
															>
																<Trash2 className="h-4 w-4 mr-2" />
																Elimina
															</DropdownMenuItem>
														</DropdownMenuContent>
													</DropdownMenu>
												</div>
											</TableCell>
										</TableRow>
									))}
								</TableBody>
							</Table>
						</div>
					)}
				</CardContent>
			</Card>
		</div>
	)
}
