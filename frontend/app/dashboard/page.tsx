'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Database, FileText, Search, Upload, Activity, CheckCircle2, Clock, AlertCircle } from 'lucide-react'
import Link from 'next/link'

// Mock data - sostituire con dati reali
const stats = {
	totalDocuments: 0,
	processed: 0,
	ragQueries: 0,
	chunks: 0,
}

const systemStatus = [
	{ name: 'Backend API', status: 'online' as const },
	{ name: 'Vector Database', status: 'pending' as const },
	{ name: 'Document Processing', status: 'pending' as const },
]

const recentActivity: Array<{
	id: string
	type: 'upload' | 'process' | 'search'
	description: string
	timestamp: string
}> = []

export default function DashboardPage() {
	const getStatusColor = (status: 'online' | 'pending' | 'error') => {
		switch (status) {
			case 'online':
				return 'text-green-600 dark:text-green-400'
			case 'pending':
				return 'text-yellow-600 dark:text-yellow-400'
			case 'error':
				return 'text-red-600 dark:text-red-400'
			default:
				return 'text-muted-foreground'
		}
	}

	const getStatusIcon = (status: 'online' | 'pending' | 'error') => {
		switch (status) {
			case 'online':
				return <CheckCircle2 className="h-4 w-4" />
			case 'pending':
				return <Clock className="h-4 w-4" />
			case 'error':
				return <AlertCircle className="h-4 w-4" />
			default:
				return null
		}
	}

	return (
		<div className="space-y-4 md:space-y-6">
			<div>
				<h2 className="text-2xl md:text-3xl font-bold tracking-tight">Dashboard</h2>
				<p className="text-sm md:text-base text-muted-foreground mt-1">
					Panoramica del sistema di gestione documenti
				</p>
			</div>

			{/* Statistiche - Grid mobile-first */}
			<div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
				<Card>
					<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
						<CardTitle className="text-xs sm:text-sm font-medium">
							Documenti Totali
						</CardTitle>
						<FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
					</CardHeader>
					<CardContent>
						<div className="text-xl sm:text-2xl font-bold">{stats.totalDocuments}</div>
						<p className="text-xs text-muted-foreground mt-1">
							{stats.totalDocuments === 0
								? 'Nessun documento caricato'
								: `${stats.processed} elaborati`}
						</p>
					</CardContent>
				</Card>

				<Card>
					<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
						<CardTitle className="text-xs sm:text-sm font-medium">
							Elaborati
						</CardTitle>
						<Upload className="h-4 w-4 text-muted-foreground flex-shrink-0" />
					</CardHeader>
					<CardContent>
						<div className="text-xl sm:text-2xl font-bold">{stats.processed}</div>
						<p className="text-xs text-muted-foreground mt-1">Pronti per ricerca</p>
					</CardContent>
				</Card>

				<Card>
					<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
						<CardTitle className="text-xs sm:text-sm font-medium">
							Ricerche RAG
						</CardTitle>
						<Search className="h-4 w-4 text-muted-foreground flex-shrink-0" />
					</CardHeader>
					<CardContent>
						<div className="text-xl sm:text-2xl font-bold">{stats.ragQueries}</div>
						<p className="text-xs text-muted-foreground mt-1">
							Ricerche effettuate
						</p>
					</CardContent>
				</Card>

				<Card>
					<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
						<CardTitle className="text-xs sm:text-sm font-medium">
							Database Vettoriale
						</CardTitle>
						<Database className="h-4 w-4 text-muted-foreground flex-shrink-0" />
					</CardHeader>
					<CardContent>
						<div className="text-xl sm:text-2xl font-bold">{stats.chunks}</div>
						<p className="text-xs text-muted-foreground mt-1">Chunk memorizzati</p>
					</CardContent>
				</Card>
			</div>

			{/* Quick Actions - Mobile first */}
			<div className="grid gap-3 sm:gap-4 sm:grid-cols-2">
				<Card>
					<CardHeader>
						<CardTitle className="text-base sm:text-lg">Azioni Rapide</CardTitle>
						<CardDescription>Operazioni frequenti</CardDescription>
					</CardHeader>
					<CardContent className="space-y-2">
						<Button asChild className="w-full" size="sm">
							<Link href="/dashboard/upload">
								<Upload className="mr-2 h-4 w-4" />
								Carica Documento
							</Link>
						</Button>
						<Button asChild variant="outline" className="w-full" size="sm">
							<Link href="/dashboard/search">
								<Search className="mr-2 h-4 w-4" />
								Ricerca RAG
							</Link>
						</Button>
						<Button asChild variant="outline" className="w-full" size="sm">
							<Link href="/dashboard/documents">
								<FileText className="mr-2 h-4 w-4" />
								Visualizza Documenti
							</Link>
						</Button>
					</CardContent>
				</Card>

				<Card>
					<CardHeader>
						<CardTitle className="text-base sm:text-lg">Stato Sistema</CardTitle>
						<CardDescription>Monitoraggio servizi</CardDescription>
					</CardHeader>
					<CardContent>
						<div className="space-y-3">
							{systemStatus.map((item) => (
								<div
									key={item.name}
									className="flex items-center justify-between gap-2"
								>
									<span className="text-xs sm:text-sm flex-1">{item.name}</span>
									<div
										className={`flex items-center gap-1 ${getStatusColor(item.status)}`}
									>
										{getStatusIcon(item.status)}
										<span className="text-xs sm:text-sm font-medium capitalize">
											{item.status === 'online' ? 'Online' : item.status === 'pending' ? 'In attesa' : 'Errore'}
										</span>
									</div>
								</div>
							))}
						</div>
					</CardContent>
				</Card>
			</div>

			{/* Recent Activity */}
			<Card>
				<CardHeader>
					<CardTitle className="text-base sm:text-lg">Attività Recente</CardTitle>
					<CardDescription>Le ultime operazioni sui documenti</CardDescription>
				</CardHeader>
				<CardContent>
					{recentActivity.length === 0 ? (
						<div className="text-center py-8">
							<Activity className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
							<p className="text-sm text-muted-foreground">
								Nessuna attività recente
							</p>
							<Button asChild variant="outline" className="mt-4" size="sm">
								<Link href="/dashboard/upload">Carica il primo documento</Link>
							</Button>
						</div>
					) : (
						<div className="space-y-3">
							{recentActivity.map((activity) => (
								<div
									key={activity.id}
									className="flex items-start gap-3 p-3 border rounded-lg"
								>
									<div className="flex-shrink-0 mt-0.5">
										{activity.type === 'upload' && (
											<Upload className="h-4 w-4 text-muted-foreground" />
										)}
										{activity.type === 'process' && (
											<Activity className="h-4 w-4 text-muted-foreground" />
										)}
										{activity.type === 'search' && (
											<Search className="h-4 w-4 text-muted-foreground" />
										)}
									</div>
									<div className="flex-1 min-w-0">
										<p className="text-sm font-medium">{activity.description}</p>
										<p className="text-xs text-muted-foreground mt-1">
											{new Date(activity.timestamp).toLocaleString('it-IT')}
										</p>
									</div>
								</div>
							))}
						</div>
					)}
				</CardContent>
			</Card>
		</div>
	)
}
