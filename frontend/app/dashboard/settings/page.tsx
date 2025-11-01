'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Settings, Sparkles, Cog, Bell, User, Shield, Palette } from 'lucide-react'
import Link from 'next/link'

export default function SettingsPage() {
	const settingsSections = [
		{ icon: User, title: 'Profilo', description: 'Gestisci le tue informazioni personali' },
		{ icon: Bell, title: 'Notifiche', description: 'Configura le notifiche del sistema' },
		{ icon: Shield, title: 'Sicurezza', description: 'Password e autenticazione' },
		{ icon: Palette, title: 'Aspetto', description: 'Tema e preferenze visuali' },
	]

	return (
		<div className="space-y-4 md:space-y-6">
			<div>
				<h2 className="text-2xl md:text-3xl font-bold tracking-tight flex items-center gap-2">
					<Sparkles className="h-6 w-6 text-primary" />
					Impostazioni
				</h2>
				<p className="text-sm md:text-base text-muted-foreground mt-1">
					Configurazione del sistema
				</p>
			</div>

			<div className="grid gap-4 md:grid-cols-2">
				{settingsSections.map((section) => (
					<Card
						key={section.title}
						className="cursor-pointer"
					>
						<CardHeader>
							<CardTitle className="flex items-center gap-3 text-base sm:text-lg">
								<div className="p-2 rounded-lg bg-primary/10">
									<section.icon className="h-5 w-5 text-primary" />
								</div>
								{section.title}
							</CardTitle>
							<CardDescription>{section.description}</CardDescription>
						</CardHeader>
						<CardContent>
							<div className="text-sm text-muted-foreground">
								Funzionalità in sviluppo
							</div>
						</CardContent>
					</Card>
				))}
			</div>

			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<Cog className="h-5 w-5 text-primary" />
						Impostazioni Sistema
					</CardTitle>
					<CardDescription>Configura le impostazioni dell'applicazione</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="text-center py-12">
						<div className="relative inline-block mb-6">
							<div className="rounded-full bg-primary/10 p-6">
								<Settings className="h-12 w-12 text-primary" />
							</div>
						</div>
						<h3 className="text-lg font-semibold mb-2">Funzionalità in sviluppo</h3>
						<p className="text-sm text-muted-foreground max-w-md mx-auto mb-6">
							Le impostazioni avanzate del sistema saranno disponibili a breve. 
							Potrai configurare API keys, preferenze di elaborazione e molto altro.
						</p>
						<Button asChild variant="outline">
							<Link href="/dashboard" className="flex items-center gap-2">
								<span>Torna alla Dashboard</span>
							</Link>
						</Button>
					</div>
				</CardContent>
			</Card>
		</div>
	)
}
