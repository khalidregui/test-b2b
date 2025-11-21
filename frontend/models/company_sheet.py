from typing import Optional

import numpy as np
import pandas as pd
from services.api_client import get_api_client


class CompanySheet:
    def __init__(self, company_id: str):
        """Initialize CompanySheet with a company ID.

        Args:
            company_id: Unique identifier for the company
        """
        self.company_id = company_id
        self.identity_data: Optional[dict] = None
        self.contact_data: Optional[dict] = None
        self.revenue_data: Optional[pd.DataFrame] = None
        self.credit_data: Optional[dict] = None
        self.partnership_data: Optional[dict] = None
        self.complaints_data: Optional[dict] = None
        self.news_data: Optional[dict] = None
        self.offers_data: Optional[dict] = None
        self.potential_data: Optional[dict] = None

    def load_all_data(self, fetch_linkedin: bool = True):
        """Load all data from the backend for this company.

        Args:
            fetch_linkedin: Whether to fetch fresh LinkedIn data for enrichment
        """
        api_client = get_api_client()

        if api_client.health_check():
            self._load_backend_data(api_client, fetch_linkedin)
        else:
            print("DEBUG: Backend not available, using mock data")
            self._load_mock_data()

    def _load_backend_data(self, api_client, fetch_linkedin: bool = True):
        """Load data from the backend API.

        Args:
            api_client: API client instance
            fetch_linkedin: Whether to fetch fresh LinkedIn data
        """
        try:
            print(f"DEBUG: Loading data for client_id: {self.company_id}")
            print(f"DEBUG: fetch_linkedin parameter: {fetch_linkedin}")

            identity_response = api_client.get_client_identity(self.company_id)
            print(f"DEBUG: Identity response: {identity_response}")

            has_excel_data = identity_response and identity_response.get("company_name") not in [
                "Données indisponibles",
                "Données non disponibles",
                None,
                "",
            ]

            if has_excel_data:
                print("DEBUG: ✅ Excel data found - Loading internal data")

                self.identity_data = self._prepare_identity_data(identity_response)
                print(f"DEBUG: Initial identity_data: {self.identity_data}")

                self._load_excel_contact_data(api_client)
                self._load_excel_receivables_data(api_client)
                self._load_excel_complaints_data(api_client)
                self._load_excel_services_data(api_client)

                if fetch_linkedin:
                    print("DEBUG: Attempting LinkedIn enrichment...")
                    self._try_linkedin_enrichment(api_client)
                else:
                    print("DEBUG: LinkedIn enrichment disabled")

                if not hasattr(self, "partnership_data") or self.partnership_data is None:
                    self._load_default_partnership_data(identity_response)
                if not hasattr(self, "news_data") or self.news_data is None:
                    self._load_default_news_data(identity_response)
                if not hasattr(self, "potential_data") or self.potential_data is None:
                    self._load_default_potential_data()

                self.revenue_data = self._generate_revenue_data()

                print(f"DEBUG: FINAL identity_data: {self.identity_data}")
                print("DEBUG: ✅ Excel data loading completed successfully")

            else:
                print("DEBUG: ❌ No valid Excel data - Using mock data")
                self._load_mock_data()

        except Exception as e:
            print(f"ERROR: Exception in _load_backend_data: {e}")
            import traceback

            traceback.print_exc()
            print("DEBUG: ❌ Exception - Fallback to mock data")
            self._load_mock_data()

    def _prepare_identity_data(self, identity_response: dict) -> dict:
        """Prepare identity data from Excel response."""
        print(f"DEBUG: Preparing identity data from: {identity_response}")

        identity_data = identity_response.copy()

        identity_data.update(
            {
                "employees": "N/A",
                "linkedin_url": "#",
                "website_url": "#",
                "address": "Données indisponibles",
                "address_link": "#",
            }
        )

        print(f"DEBUG: Prepared identity data: {identity_data}")
        return identity_data

    def _try_linkedin_enrichment(self, api_client):
        """Try to enrich data with LinkedIn (non-blocking)."""
        try:
            print("DEBUG: Attempting LinkedIn enrichment...")

            scrapping_response = api_client.get_client_scraping_llm(
                self.company_id, fetch_linkedin=True
            )

            print(f"DEBUG: Scrapping response received: {scrapping_response}")

            if scrapping_response and "identity_enrichment" in scrapping_response:
                print("DEBUG: LinkedIn enrichment successful")
                enrichment = scrapping_response["identity_enrichment"]

                if (
                    enrichment.get("employees")
                    and enrichment["employees"] != "Données indisponibles"
                ):
                    self.identity_data["employees"] = enrichment["employees"]
                    print(f"DEBUG: Updated employees: {enrichment['employees']}")

                if (
                    enrichment.get("linkedin_url")
                    and enrichment["linkedin_url"] != "Données indisponibles"
                ):
                    self.identity_data["linkedin_url"] = enrichment["linkedin_url"]
                    print(f"DEBUG: Updated linkedin_url: {enrichment['linkedin_url']}")

                if (
                    enrichment.get("website_url")
                    and enrichment["website_url"] != "Données indisponibles"
                ):
                    website_url = enrichment["website_url"]
                    if not website_url.startswith(("http://", "https://")):
                        website_url = f"https://{website_url}"
                    self.identity_data["website_url"] = website_url
                    print(f"DEBUG: Updated website_url: {website_url}")

                if enrichment.get("address") and enrichment["address"] != "Données indisponibles":
                    self.identity_data["address"] = enrichment["address"]
                    address_encoded = enrichment["address"].replace(" ", "+").replace(",", "%2C")
                    self.identity_data["address_link"] = (
                        f"https://www.google.com/maps/search/?api=1&query={address_encoded}"
                    )
                    print(f"DEBUG: Updated address: {enrichment['address']}")

                if (
                    enrichment.get("activity_linkedin")
                    and enrichment["activity_linkedin"] != "Données indisponibles"
                ):
                    self.identity_data["activity_excel"] = self.identity_data.get("activity", "")
                    self.identity_data["activity"] = enrichment["activity_linkedin"]
                    print(
                        f"DEBUG: Replaced activity with LinkedIn activity: {enrichment['activity_linkedin']}"
                    )
                    print(
                        f"DEBUG: Excel activity saved as backup: {self.identity_data['activity_excel']}"
                    )

                self._extract_partnership_data(scrapping_response)
                self._extract_news_data(scrapping_response)
                self._extract_potential_data(scrapping_response)

                print(f"DEBUG: Final identity_data after LinkedIn enrichment: {self.identity_data}")
                print("DEBUG: LinkedIn enrichment applied successfully")
            else:
                print("DEBUG: No LinkedIn enrichment data available")

        except Exception as e:
            print(f"DEBUG: LinkedIn enrichment failed (non-critical): {e}")
            import traceback

            traceback.print_exc()

    def _load_excel_contact_data(self, api_client):
        """Load contact data from Excel."""
        try:
            contact_response = api_client.get_client_contact(self.company_id)
            if contact_response and contact_response.get("name") not in [
                "Données indisponibles",
                None,
                "",
            ]:
                self.contact_data = contact_response
                print(f"DEBUG: Contact data loaded: {contact_response}")
            else:
                print("DEBUG: No valid contact data, using mock")
                self._load_mock_contact_data()
        except Exception as e:
            print(f"DEBUG: Error loading contact data: {e}")
            self._load_mock_contact_data()

    def _load_excel_receivables_data(self, api_client):
        """Load receivables data from Excel."""
        try:
            receivables_response = api_client.get_client_receivables(self.company_id)
            if receivables_response and receivables_response.get("status") not in [
                "Données indisponibles",
                None,
                "",
            ]:
                self.credit_data = receivables_response
                print(f"DEBUG: Receivables data loaded: {receivables_response}")
            else:
                print("DEBUG: No valid receivables data, using mock")
                self._load_mock_credit_data()
        except Exception as e:
            print(f"DEBUG: Error loading receivables data: {e}")
            self._load_mock_credit_data()

    def _load_excel_complaints_data(self, api_client):
        """Load complaints data from Excel."""
        try:
            complaints_response = api_client.get_client_complaints(self.company_id)
            if complaints_response and len(complaints_response) > 0:
                first_complaint = complaints_response[0]
                if first_complaint.get("title") not in ["Données indisponibles", None, ""]:
                    self.complaints_data = {
                        "title": first_complaint.get("title", "Aucune réclamation récente"),
                        "description": first_complaint.get(
                            "description", "Le client n'a pas de réclamations en cours."
                        ),
                        "resolution": first_complaint.get("resolution", "N/A"),
                    }
                    print(f"DEBUG: Complaints data loaded: {self.complaints_data}")
                    return

            print("DEBUG: No valid complaints data, using mock")
            self._load_mock_complaints_data()
        except Exception as e:
            print(f"DEBUG: Error loading complaints data: {e}")
            self._load_mock_complaints_data()

    def _load_excel_services_data(self, api_client):
        """Load services data from Excel."""
        try:
            services_response = api_client.get_client_services(self.company_id)
            if services_response and len(services_response) > 0:
                first_service = services_response[0]
                if first_service.get("service_name") not in ["Données indisponibles", None, ""]:
                    self._extract_offers_data(services_response)
                    print(f"DEBUG: Services data loaded: {services_response}")
                    return

            print("DEBUG: No valid services data, using mock")
            self._load_mock_offers_data()
        except Exception as e:
            print(f"DEBUG: Error loading services data: {e}")
            self._load_mock_offers_data()

    def _load_default_partnership_data(self, identity_response: dict):
        """Load default partnership data based on Excel data."""
        self.partnership_data = {
            "start_date": 2020,
            "description": "",  # ✅ Description vide par défaut
            "points": [],       # ✅ Points vides par défaut
        }

    def _load_default_news_data(self, identity_response: dict):
        """Load default news data based on Excel data."""
        activity = identity_response.get("activity", "le secteur")
        company_name = identity_response.get("company_name", "l'entreprise")

        self.news_data = {
            "sector_context": [f"Évolution du secteur {activity}"],
            "cybersecurity_focus": ["Renforcement de la sécurité"],
            "company_news": [f"Actualités de {company_name}"],
        }

    def _load_default_potential_data(self):
        """Load default potential data."""
        self.potential_data = {
            "ongoing_acquisitions": ["Projets en cours d'évaluation"],
            "upsell_cross_sell": ["Opportunités commerciales à identifier"],
        }

    def _extract_partnership_data(self, scrapping_response: dict):
        """Extract partnership data from scrapping response."""
        # ✅ Ne plus utiliser partnership_summary, garder vide par défaut
        self.partnership_data = {
            "start_date": 2020,
            "description": "",  # Description vide par défaut
            "points": [],       # Points vides par défaut
        }

    def _extract_news_data(self, scrapping_response: dict):
        """Extract news data from scrapping response."""
        news = scrapping_response.get("news", {})

        self.news_data = {
            "sector_context": news.get("sector_context", ["Évolution du secteur en cours"]),
            "cybersecurity_focus": news.get("cybersecurity_focus", ["Renforcement de la sécurité"]),
            "company_news": news.get("company_news", ["Actualités de l'entreprise"]),
        }

    def _extract_potential_data(self, scrapping_response: dict):
        """Extract potential data from scrapping response."""
        potential = scrapping_response.get("potential", {})

        self.potential_data = {
            "ongoing_acquisitions": potential.get(
                "ongoing_acquisitions", ["Projets en cours d'évaluation"]
            ),
            "upsell_cross_sell": potential.get(
                "upsell_cross_sell", ["Opportunités commerciales à identifier"]
            ),
        }

    def _extract_offers_data(self, services_response: list):
        """Extract offers data from services response."""
        internet_services = []
        voice_services = []

        for service in services_response:
            service_name = service.get("service_name", "")
            category = service.get("category", "").lower()
            status = service.get("status", "")

            service_display = f"{service_name}"
            if status and status != "Données indisponibles":
                service_display += f" ({status})"

            if "internet" in category or "data" in category or "cloud" in category:
                internet_services.append(service_display)
            elif "voice" in category or "mobile" in category or "phone" in category:
                voice_services.append(service_display)
            else:
                internet_services.append(service_display)

        if not internet_services:
            internet_services = ["Services Internet Orange Business"]
        if not voice_services:
            voice_services = ["Services Voix Orange Business"]

        self.offers_data = {
            "internet": internet_services,
            "voice": voice_services,
        }

    def _load_mock_contact_data(self):
        """Load mock contact data."""
        self.contact_data = {
            "name": "Contact Principal",
            "phone": "+226 XX XX XX XX",
            "email": "contact@client.com",
        }

    def _load_mock_credit_data(self):
        """Load mock credit data."""
        self.credit_data = {
            "status": "À jour",
            "amount": 0,
            "average_age": 0,
            "risk_level": "Risque Faible",
            "total_amount": 0,
        }

    def _load_mock_complaints_data(self):
        """Load mock complaints data."""
        self.complaints_data = {
            "title": "Aucune réclamation récente",
            "description": "Le client n'a pas de réclamations en cours.",
            "resolution": "N/A",
        }

    def _load_mock_offers_data(self):
        """Load mock offers data."""
        self.offers_data = {
            "internet": ["Internet dédié : Siège", "Connectivité MPLS", "Solutions Cloud"],
            "voice": ["Téléphonie d'entreprise", "Services mobiles", "Messagerie professionnelle"],
        }

    def _load_mock_partnership_data(self):
        """Load mock partnership data."""
        self.partnership_data = {
            "start_date": 2021,
            "description": "Partenariat stratégique en développement.",
            "points": ["Solutions de connectivité", "Services numériques", "Support technique"],
        }

    def _load_mock_news_data(self):
        """Load mock news data."""
        self.news_data = {
            "sector_context": ["Évolution du secteur"],
            "cybersecurity_focus": ["Sécurité renforcée"],
            "company_news": ["Actualités de l'entreprise"],
        }

    def _load_mock_potential_data(self):
        """Load mock potential data."""
        self.potential_data = {
            "ongoing_acquisitions": ["Projets en cours"],
            "upsell_cross_sell": ["Opportunités commerciales"],
        }

    def _load_mock_data(self):
        """Load mock data for development and testing purposes."""
        print("DEBUG: Loading complete mock data set")

        self.identity_data = {
            "company_name": "Bank Of Africa",
            "ceo": "Farid Bouri",
            "activity": "Banques / Assurance",
            "employees": "500-1 000 employés",
            "address": "Av. du Général Sangoulé Lamizana, Koulouba, Ouagadougou, Burkina Faso",
            "address_link": "https://www.google.com/maps/search/?api=1&query=Av.+du+Général+Sangoulé+Lamizana,+Koulouba,+Ouagadougou,+Burkina+Faso",
            "other_addresses": "Pas de donnée disponible",
            "linkedin_url": "https://www.linkedin.com/company/bank-of-africa",
            "website_url": "https://www.bank-of-africa.net",
        }

        self._load_mock_contact_data()
        self._load_mock_credit_data()
        self._load_mock_partnership_data()
        self._load_mock_complaints_data()
        self._load_mock_news_data()
        self._load_mock_offers_data()
        self._load_mock_potential_data()

        self.revenue_data = self._generate_revenue_data()

    def _generate_revenue_data(self):
        """Generate mock revenue data for Orange Business Services products."""
        produits = [
            "Orange Business Internet",
            "Orange Flexible SD-WAN",
            "Orange Business Mobile",
            "Orange Cloud for Business",
            "Orange Cyberdefense",
            "Orange Business VoIP",
        ]

        dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")

        data = []
        for date in dates:
            for produit in produits:
                base_revenue = {
                    "Orange Business Internet": 18000000,
                    "Orange Flexible SD-WAN": 12000000,
                    "Orange Business Mobile": 15000000,
                    "Orange Cloud for Business": 8000000,
                    "Orange Cyberdefense": 6000000,
                    "Orange Business VoIP": 4000000,
                }

                daily_revenue = base_revenue[produit] / 365 * (0.8 + 0.4 * np.random.random())

                data.append(
                    {
                        "Date": date,
                        "Produit": produit,
                        "Revenu": daily_revenue,
                        "Année": date.year,
                        "Mois": date.strftime("%Y-%m"),
                        "Semaine": date.strftime("%Y-W%U"),
                    }
                )

        return pd.DataFrame(data)

    def get_cache_info(self):
        """Get cache information from the backend."""
        api_client = get_api_client()
        return api_client.get_cache_info()

    def clear_cache(self):
        """Clear the backend cache."""
        api_client = get_api_client()
        return api_client.clear_cache()

    def refresh_cache(self):
        """Force refresh the backend cache."""
        api_client = get_api_client()
        return api_client.refresh_cache()

    def reload_data(self, fetch_linkedin: bool = True):
        """Reload all data from the backend.

        Args:
            fetch_linkedin: Whether to fetch fresh LinkedIn data
        """
        self.load_all_data(fetch_linkedin=fetch_linkedin)
    
    def update_partnership_description(self, description: str) -> bool:
        """Update partnership description via API.
        
        Args:
            description: New partnership description
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"🔍 DEBUG CompanySheet: Début mise à jour pour client_id={self.company_id}")
            print(f"🔍 DEBUG CompanySheet: Description={description[:100]}...")
            
            api_client = get_api_client()
            print(f"🔍 DEBUG CompanySheet: API client obtenu, base_url={api_client.base_url}")
            
            print(f"🔍 DEBUG CompanySheet: URL complète sera: {api_client.base_url}/api/clients/{self.company_id}/partnership/update-description")
            
            result = api_client.update_partnership_description(self.company_id, description)
            print(f"🔍 DEBUG CompanySheet: Résultat de l'API: {result}")
            
            if result and result.get("success"):
                print("🔍 DEBUG CompanySheet: Succès API - Mise à jour des données locales")
                # Mettre à jour les données locales
                if self.partnership_data:
                    self.partnership_data["description"] = description
                else:
                    self.partnership_data = {
                        "start_date": 2020,
                        "description": description,
                        "points": []
                    }
                print("🔍 DEBUG CompanySheet: Données locales mises à jour")
                return True
            else:
                print(f"🔍 DEBUG CompanySheet: Échec API - result={result}")
                return False
            
        except Exception as e:
            print(f"❌ ERROR CompanySheet: Exception complète: {e}")
            import traceback
            traceback.print_exc()
            return False

