'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Database, Package, Sparkles, Rocket } from 'lucide-react'
import Link from 'next/link'
import { cn } from '@/lib/utils'

export default function DatabasePage() {
	return (
		<div className="space-y-4 md:space-y-6">
			<div>
				<h2 className="text-2xl md:text-3xl font-bold tracking-tight flex items-center gap-2">
					<Sparkles className="h-6 w-6 text-primary" />
					Database Vettoriale
				</h2>
				<p className="text-sm md:text-base text-muted-foreground mt-1">
					Gestione del database vettoriale Qdrant
				</p>
			</div>

			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<Database className="h-5 w-5 text-primary" />
						Stato Database
					</CardTitle>
					<CardDescription>Informazioni sul database vettoriale</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="text-center py-16">
						<div className="relative inline-block mb-6">
							<div className="rounded-full bg-primary/10 p-6">
								<Database className="h-12 w-12 text-primary" />
							</div>
						</div>
						<h3 className="text-lg font-semibold mb-2">Funzionalità in sviluppo</h3>
						<p className="text-sm text-muted-foreground max-w-md mx-auto mb-6">
							Il pannello di gestione del database vettoriale sarà disponibile a breve. 
							Potrai visualizzare statistiche, gestire le collezioni e monitorare le performance.
						</p>
						<div className="flex flex-col sm:flex-row gap-3 justify-center">
							<Button asChild variant="outline">
								<Link href="/dashboard/documents" className="flex items-center gap-2">
									<Package className="h-4 w-4" />
									Visualizza Documenti
								</Link>
							</Button>
							<Button asChild>
								<Link href="/dashboard/search" className="flex items-center gap-2">
									<Rocket className="h-4 w-4" />
									Prova Chat AI
								</Link>
							</Button>
						</div>
					</div>
				</CardContent>
			</Card>
		</div>
	)
}
