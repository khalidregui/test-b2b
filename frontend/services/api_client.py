"""API client for communicating with the B2B Meeting Assistant backend."""

from typing import Any, Dict, List, Optional

import requests
import streamlit as st


class APIClient:
    """Client for interacting with the B2B Meeting Assistant API."""

    def __init__(self, base_url: str = "http://backend:8000"):
        """Initialize the API client.

        Args:
            base_url: Base URL of the backend API
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and error checking.

        Args:
            response: HTTP response object

        Returns:
            dict: Parsed JSON response

        Raises:
            requests.HTTPError: If the request was unsuccessful
        """
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError:
            raise
        except ValueError:
            raise

    def get_cache_info(self) -> Optional[Dict[str, Any]]:
        """Get cache information from the backend.

        Returns:
            Cache information or None if error
        """
        try:
            response = self.session.get(f"{self.base_url}/api/cache/info")
            return self._handle_response(response)
        except Exception:
            return None

    def clear_cache(self) -> bool:
        """Clear the backend cache.

        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.post(f"{self.base_url}/api/cache/clear")
            self._handle_response(response)
            return True
        except Exception:
            return False

    def refresh_cache(self) -> Optional[Dict[str, Any]]:
        """Force refresh the backend cache.

        Returns:
            Cache refresh result or None if error
        """
        try:
            response = self.session.post(f"{self.base_url}/api/cache/refresh")
            return self._handle_response(response)
        except Exception:
            return None

    def autocomplete_clients(
        self, query: str, country: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Get autocomplete suggestions for client search.

        Args:
            query: Search query string
            country: Country code (optional)

        Returns:
            List of client suggestions
        """
        try:
            params = {"q": query}
            if country:
                params["country"] = country

            response = self.session.get(f"{self.base_url}/api/clients/autocomplete", params=params)
            results = self._handle_response(response)

            transformed_results = []
            for result in results:
                result_type = result.get("type", "")

                if result_type == "identifier":
                    client_id = result.get("value", "")
                    label = result.get("label", "")
                    if " - " in label:
                        company_name = label.split(" - ", 1)[1]
                    else:
                        company_name = label

                elif result_type == "company_name":
                    company_name = result.get("value", "")
                    label = result.get("label", "")
                    if "(" in label and ")" in label:
                        client_id = label.split("(")[1].split(")")[0]
                    else:
                        continue
                else:
                    continue

                if client_id and company_name:
                    transformed_results.append(
                        {"identifier": client_id, "company_name": company_name, "activity": "N/A"}
                    )

            return transformed_results
        except Exception as e:
            st.error(f"Erreur lors de l'autocomplétion : {e}")
            return []

    def search_clients(
        self, identifier: Optional[str] = None, company_name: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Search for clients by identifier or company name.

        Args:
            identifier: Client identifier or search query
            company_name: Company name

        Returns:
            List of matching clients
        """
        params = {}
        if identifier:
            params["identifier"] = identifier
        if company_name:
            params["company_name"] = company_name

        try:
            response = self.session.get(f"{self.base_url}/api/clients/search", params=params)
            results = self._handle_response(response)

            for result in results:
                if "client_id" in result and "identifier" not in result:
                    result["identifier"] = result["client_id"]

            return results
        except Exception:
            return []

    def get_client_identity(
        self, client_id: str, country: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get client identity data.

        Args:
            client_id: Client identifier
            country: Country code (optional)

        Returns:
            Client identity data or None if not found
        """
        try:
            params = {}
            if country:
                params["country"] = country

            response = self.session.get(
                f"{self.base_url}/api/clients/{client_id}/identity", params=params
            )
            return self._handle_response(response)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "company_name": "Données indisponibles",
                    "ceo": "Données indisponibles",
                    "activity": "Données indisponibles",
                    "other_addresses": "Données indisponibles",
                    "country": "BF",
                }
            raise
        except Exception:
            return {
                "company_name": "Données indisponibles",
                "ceo": "Données indisponibles",
                "activity": "Données indisponibles",
                "other_addresses": "Données indisponibles",
                "country": "BF",
            }

    def get_client_contact(
        self, client_id: str, country: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get client contact data.

        Args:
            client_id: Client identifier
            country: Country code (optional)

        Returns:
            Client contact data or None if not found
        """
        try:
            params = {}
            if country:
                params["country"] = country

            response = self.session.get(
                f"{self.base_url}/api/clients/{client_id}/contact", params=params
            )
            return self._handle_response(response)
        except Exception:
            return {
                "name": "Données indisponibles",
                "phone": "Données indisponibles",
                "email": "Données indisponibles",
            }

    def get_client_receivables(
        self, client_id: str, country: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get client receivables data.

        Args:
            client_id: Client identifier
            country: Country code (optional)

        Returns:
            Client receivables data or None if not found
        """
        try:
            params = {}
            if country:
                params["country"] = country

            response = self.session.get(
                f"{self.base_url}/api/clients/{client_id}/receivables", params=params
            )
            return self._handle_response(response)
        except Exception:
            return {
                "status": "Données indisponibles",
                "amount": "Données indisponibles",
                "average_age": "Données indisponibles",
                "risk_level": "Données indisponibles",
                "total_amount": "Données indisponibles",
            }

    def update_partnership_description(
        self, client_id: str, description: str
    ) -> Optional[Dict[str, Any]]:
        """Update client partnership description via GET request.

        Args:
            client_id: Client identifier
            description: New partnership description

        Returns:
            Update result or None if error
        """
        try:
            params = {"description": description}
            response = self.session.get(
                f"{self.base_url}/api/clients/{client_id}/partnership/update-description",
                params=params
            )
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Erreur lors de la mise à jour de la description : {e}")
            return None

    # Modifier la méthode get_client_partnership existante pour retourner une description vide par défaut :

    def get_client_partnership(
        self, client_id: str, country: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get client partnership data.

        Args:
            client_id: Client identifier
            country: Country code (optional)

        Returns:
            Client partnership data or None if not found
        """
        try:
            params = {}
            if country:
                params["country"] = country

            response = self.session.get(
                f"{self.base_url}/api/clients/{client_id}/partnership", params=params
            )
            return self._handle_response(response)
        except Exception:
            return {
                "start_date": 2020,
                "description": "",  # ✅ MODIFIÉ : Description vide par défaut
                "points": [],       # ✅ MODIFIÉ : Points vides par défaut
            }

    def get_client_revenues(
        self,
        client_id: str,
        country: Optional[str] = None,
        period: str = "monthly",
        products: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get client revenue data.

        Args:
            client_id: Client identifier
            country: Country code (optional)
            period: Period filter (monthly, weekly, daily)
            products: Comma-separated product list
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of revenue records
        """
        params = {"period": period}
        if country:
            params["country"] = country
        if products:
            params["products"] = products
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        try:
            response = self.session.get(
                f"{self.base_url}/api/clients/{client_id}/revenues", params=params
            )
            return self._handle_response(response)
        except Exception:
            return []

    def get_client_complaints(
        self,
        client_id: str,
        country: Optional[str] = None,
        product: Optional[str] = None,
        complaint_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get client complaints data.

        Args:
            client_id: Client identifier
            country: Country code (optional)
            product: Product filter
            complaint_type: Complaint type filter

        Returns:
            List of complaints
        """
        params = {}
        if country:
            params["country"] = country
        if product:
            params["product"] = product
        if complaint_type:
            params["complaint_type"] = complaint_type

        try:
            response = self.session.get(
                f"{self.base_url}/api/clients/{client_id}/complaints", params=params
            )
            return self._handle_response(response)
        except Exception:
            return [
                {
                    "title": "Données indisponibles",
                    "description": "Données indisponibles",
                    "resolution": "Données indisponibles",
                    "product": "Données indisponibles",
                    "type": "Données indisponibles",
                }
            ]

    def get_client_services(
        self, client_id: str, country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get client services data.

        Args:
            client_id: Client identifier
            country: Country code (optional)

        Returns:
            List of services
        """
        try:
            params = {}
            if country:
                params["country"] = country

            response = self.session.get(
                f"{self.base_url}/api/clients/{client_id}/services", params=params
            )
            return self._handle_response(response)
        except Exception:
            return [
                {
                    "service_name": "Données indisponibles",
                    "category": "Données indisponibles",
                    "status": "Données indisponibles",
                }
            ]

    def get_client_scraping_llm(
        self, client_id: str, country: Optional[str] = None, fetch_linkedin: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get client scraping and LLM data.

        Args:
            client_id: Client identifier
            country: Country code (optional)
            fetch_linkedin: Whether to fetch fresh LinkedIn data

        Returns:
            Scraping and LLM data or None if not found
        """
        try:
            params = {}
            if country:
                params["country"] = country
            if not fetch_linkedin:
                params["fetch_linkedin"] = "false"

            response = self.session.get(
                f"{self.base_url}/api/clients/{client_id}/scrapping_and_llm", params=params
            )
            return self._handle_response(response)
        except Exception:
            return {
                "identity_enrichment": {
                    "employees": "Données indisponibles",
                    "linkedin_url": "Données indisponibles",
                    "website_url": "Données indisponibles",
                    "address": "Données indisponibles",
                    "activity_linkedin": "Données indisponibles",
                },
                "partnership_summary": "Données indisponibles",
                "news": {
                    "sector_context": ["Données indisponibles"],
                    "cybersecurity_focus": ["Données indisponibles"],
                    "company_news": ["Données indisponibles"],
                },
                "potential": {
                    "ongoing_acquisitions": ["Données indisponibles"],
                    "upsell_cross_sell": ["Données indisponibles"],
                },
            }

    def health_check(self) -> bool:
        """Check if the API is healthy.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return True
        except Exception:
            return False


@st.cache_resource
def get_api_client() -> APIClient:
    """Get a cached instance of the API client."""
    return APIClient()
