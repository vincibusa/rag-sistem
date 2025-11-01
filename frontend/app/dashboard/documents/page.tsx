'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
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
import { FileText, Download, Search, Filter } from 'lucide-react'

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

	const documents = mockDocuments.filter((doc) => {
		const matchesSearch = doc.name.toLowerCase().includes(searchQuery.toLowerCase())
		const matchesType = filterType === 'all' || doc.type === filterType
		const matchesStatus = filterStatus === 'all' || doc.status === filterStatus
		return matchesSearch && matchesType && matchesStatus
	})

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
				return <Badge variant="default">Pronto</Badge>
			case 'error':
				return <Badge variant="destructive">Errore</Badge>
			default:
				return null
		}
	}

	const handleDownload = async (documentId: string) => {
		// TODO: Implementare download reale
		console.log('Download document:', documentId)
	}

	return (
		<div className="space-y-4 md:space-y-6">
			<div>
				<h2 className="text-2xl md:text-3xl font-bold tracking-tight">Documenti</h2>
				<p className="text-sm md:text-base text-muted-foreground mt-1">
					Gestisci e visualizza i tuoi documenti caricati
				</p>
			</div>

			<Card>
				<CardHeader>
					<CardTitle>Lista Documenti</CardTitle>
					<CardDescription>
						{documents.length} documento{documents.length !== 1 ? 'i' : ''} trovato
						{documents.length !== mockDocuments.length && ` su ${mockDocuments.length}`}
					</CardDescription>
				</CardHeader>
				<CardContent>
					{/* Filtri e ricerca - mobile first */}
					<div className="space-y-3 mb-4">
						<div className="relative">
							<Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
							<Input
								placeholder="Cerca documenti..."
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.target.value)}
								className="pl-9"
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

					{documents.length === 0 ? (
						<div className="text-center py-12">
							<FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
							<p className="text-sm text-muted-foreground mb-2">
								{mockDocuments.length === 0
									? 'Nessun documento caricato'
									: 'Nessun documento corrisponde ai filtri'}
							</p>
							{mockDocuments.length === 0 && (
								<Button asChild className="mt-4">
									<a href="/dashboard/upload">Carica il primo documento</a>
								</Button>
							)}
						</div>
					) : (
						<div className="overflow-x-auto">
							<Table>
								<TableHeader>
									<TableRow>
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
										<TableRow key={doc.id}>
											<TableCell className="font-medium">
												<div className="flex items-center gap-2">
													<FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
													<span className="truncate">{doc.name}</span>
												</div>
												<div className="text-xs text-muted-foreground mt-1 sm:hidden">
													{doc.type} • {formatFileSize(doc.size)}
												</div>
											</TableCell>
											<TableCell className="hidden sm:table-cell">{doc.type}</TableCell>
											<TableCell className="hidden md:table-cell">
												{formatFileSize(doc.size)}
											</TableCell>
											<TableCell className="hidden lg:table-cell">
												{formatDate(doc.uploadedAt)}
											</TableCell>
											<TableCell>{getStatusBadge(doc.status)}</TableCell>
											<TableCell className="text-right">
												<Button
													variant="ghost"
													size="icon"
													onClick={() => handleDownload(doc.id)}
													className="h-8 w-8"
												>
													<Download className="h-4 w-4" />
												</Button>
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
