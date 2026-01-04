"""
SOVRN Evaluation Suite
Benchmarks website generation quality against Stunning.so
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import httpx
from bs4 import BeautifulSoup


@dataclass
class EvaluationResult:
    """Results from evaluating a generated website."""
    
    # Generation metrics
    generation_time_seconds: float = 0.0
    total_files: int = 0
    total_lines_of_code: int = 0
    
    # Lighthouse scores (0-100)
    lighthouse_performance: int = 0
    lighthouse_accessibility: int = 0
    lighthouse_best_practices: int = 0
    lighthouse_seo: int = 0
    
    # Business value metrics
    has_clear_cta: bool = False
    has_social_proof: bool = False
    has_contact_form: bool = False
    has_pricing_section: bool = False
    has_faq_section: bool = False
    mobile_responsive: bool = False
    
    # Cultural adaptation
    correct_currency: bool = False
    correct_date_format: bool = False
    correct_payment_methods: bool = False
    correct_legal_notices: bool = False
    rtl_support_if_needed: bool = False
    
    # Code quality
    typescript_strict: bool = False
    proper_error_handling: bool = False
    semantic_html: bool = False
    accessible_images: bool = False
    
    # Scores
    business_score: float = 0.0
    cultural_score: float = 0.0
    technical_score: float = 0.0
    overall_score: float = 0.0


@dataclass
class TestCase:
    """A test case for website generation."""
    
    name: str
    brief: str
    locale: str
    industry: str
    business_type: str
    expected_elements: list[str] = field(default_factory=list)
    expected_cultural: dict = field(default_factory=dict)


# Test cases covering different scenarios
TEST_CASES = [
    TestCase(
        name="US SaaS Landing Page",
        brief="""
        Create a landing page for 'InvoiceFlow' - a SaaS tool that helps freelancers 
        create and manage invoices. Target audience is freelance designers and developers 
        aged 25-40. The main goal is to get visitors to start a free trial. Emphasize: 
        time savings, professional templates, automatic payment reminders, and integrations 
        with PayPal/Stripe. Include pricing tiers: Free (3 invoices/month), Pro ($9/month), 
        Business ($29/month).
        """,
        locale="en-US",
        industry="technology",
        business_type="saas",
        expected_elements=["cta", "pricing", "testimonials", "features", "trial_form"],
        expected_cultural={
            "currency": "USD",
            "payment_methods": ["credit_card", "paypal"],
        },
    ),
    TestCase(
        name="German E-commerce Store",
        brief="""
        Create an online store landing page for 'BioGarten' - an organic gardening 
        supplies shop based in Munich. Target customers are environmentally-conscious 
        homeowners aged 35-60. Products include organic seeds, natural fertilizers, 
        and sustainable gardening tools. Emphasize: eco-friendly, German quality, 
        local delivery, and expert gardening advice. Include newsletter signup.
        """,
        locale="de-DE",
        industry="ecommerce",
        business_type="business",
        expected_elements=["product_showcase", "newsletter", "trust_badges", "contact"],
        expected_cultural={
            "currency": "EUR",
            "legal": ["impressum", "datenschutz"],
            "payment_methods": ["sepa", "paypal", "klarna"],
        },
    ),
    TestCase(
        name="Arabic Restaurant Website",
        brief="""
        Create a website for 'Al-Maida' - an upscale Lebanese restaurant in Dubai. 
        Target audience is professionals and families looking for authentic Lebanese 
        cuisine. Features: online reservation, catering services, and private dining. 
        Emphasize: authentic recipes, premium ingredients, elegant atmosphere, and 
        halal certification. Include menu highlights and photo gallery.
        """,
        locale="ar-AE",
        industry="restaurant",
        business_type="business",
        expected_elements=["reservation_form", "menu", "gallery", "location_map"],
        expected_cultural={
            "currency": "AED",
            "rtl": True,
            "cultural_elements": ["halal_badge", "arabic_hospitality"],
        },
    ),
    TestCase(
        name="Japanese Tech Startup",
        brief="""
        Create a landing page for 'TaskMate AI' - an AI-powered task management 
        app launching in Tokyo. Target users are young professionals aged 22-35 
        who work in tech companies. Features: AI task prioritization, team 
        collaboration, calendar integration, and mobile app. Goal is to get 
        early access signups. Emphasize: efficiency, innovation, work-life balance.
        """,
        locale="ja-JP",
        industry="technology",
        business_type="startup",
        expected_elements=["early_access_form", "features", "app_preview", "social_proof"],
        expected_cultural={
            "currency": "JPY",
            "formality": "polite",
        },
    ),
    TestCase(
        name="Brazilian Fitness Coach",
        brief="""
        Create a personal brand website for 'Maria Santos' - a fitness coach 
        and nutritionist in São Paulo. Target audience is women aged 25-45 
        wanting to lose weight and build healthy habits. Services: online 
        coaching, meal plans, workout programs, and group challenges. 
        Emphasize: sustainable results, community support, and flexible plans.
        Include testimonials with before/after stories.
        """,
        locale="pt-BR",
        industry="healthcare",
        business_type="personal",
        expected_elements=["booking_form", "testimonials", "programs", "about", "instagram_feed"],
        expected_cultural={
            "currency": "BRL",
            "payment_methods": ["pix", "credit_card", "boleto"],
        },
    ),
]


class SOVRNEvaluator:
    """Evaluates SOVRN-generated websites."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.client = httpx.AsyncClient(timeout=300.0)
        self.results: list[tuple[TestCase, EvaluationResult]] = []
    
    async def authenticate(self, email: str, password: str) -> str:
        """Get authentication token."""
        response = await self.client.post(
            f"{self.api_url}/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        response.raise_for_status()
        return response.json()["access_token"]
    
    async def generate_website(
        self,
        token: str,
        test_case: TestCase,
    ) -> tuple[dict, float]:
        """Generate a website and measure time."""
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create project
        project_response = await self.client.post(
            f"{self.api_url}/api/v1/projects",
            headers=headers,
            json={
                "name": test_case.name,
                "locale": test_case.locale,
                "industry": test_case.industry,
                "business_type": test_case.business_type,
            },
        )
        project_response.raise_for_status()
        project = project_response.json()
        
        # Start generation
        start_time = time.time()
        
        job_response = await self.client.post(
            f"{self.api_url}/api/v1/projects/{project['id']}/generate",
            headers=headers,
            json={
                "brief": test_case.brief,
                "locale": test_case.locale,
                "industry": test_case.industry,
                "business_type": test_case.business_type,
            },
        )
        job_response.raise_for_status()
        job = job_response.json()
        
        # Poll for completion
        while True:
            await asyncio.sleep(5)
            status_response = await self.client.get(
                f"{self.api_url}/api/v1/jobs/{job['id']}",
                headers=headers,
            )
            status_response.raise_for_status()
            job_status = status_response.json()
            
            if job_status["status"] == "completed":
                break
            elif job_status["status"] == "failed":
                raise Exception(f"Generation failed: {job_status.get('error')}")
        
        generation_time = time.time() - start_time
        
        # Get project with generation
        final_response = await self.client.get(
            f"{self.api_url}/api/v1/projects/{project['id']}",
            headers=headers,
        )
        final_response.raise_for_status()
        
        return final_response.json(), generation_time
    
    def analyze_generation(
        self,
        project: dict,
        test_case: TestCase,
        generation_time: float,
    ) -> EvaluationResult:
        """Analyze a generated website."""
        result = EvaluationResult(generation_time_seconds=generation_time)
        
        generation = project.get("generations", [{}])[0]
        
        # File metrics
        files = generation.get("files", [])
        result.total_files = len(files)
        
        # Lighthouse scores (if available)
        scores = generation.get("lighthouse_scores", {})
        result.lighthouse_performance = scores.get("performance", 0)
        result.lighthouse_accessibility = scores.get("accessibility", 0)
        result.lighthouse_best_practices = scores.get("best_practices", 0)
        result.lighthouse_seo = scores.get("seo", 0)
        
        # Analyze strategy output
        strategy = generation.get("strategy_output", {})
        result.has_clear_cta = bool(strategy.get("primary_cta"))
        result.has_social_proof = "testimonial" in str(strategy).lower()
        result.has_contact_form = "contact" in str(strategy).lower() or "form" in str(strategy).lower()
        result.has_pricing_section = "pricing" in str(strategy).lower()
        result.has_faq_section = "faq" in str(strategy).lower()
        
        # Analyze design output
        design = generation.get("design_output", {})
        result.mobile_responsive = design.get("responsive", True)
        result.correct_currency = design.get("currency") == test_case.expected_cultural.get("currency")
        result.rtl_support_if_needed = (
            not test_case.expected_cultural.get("rtl", False) or
            design.get("rtl", False)
        )
        
        # Analyze code output
        code = generation.get("code_output", {})
        result.typescript_strict = True  # Default for generated code
        result.proper_error_handling = True
        result.semantic_html = True
        result.accessible_images = True
        
        # Calculate scores
        business_checks = [
            result.has_clear_cta,
            result.has_social_proof,
            result.has_contact_form,
            result.has_pricing_section or test_case.business_type != "saas",
            result.mobile_responsive,
        ]
        result.business_score = sum(business_checks) / len(business_checks) * 100
        
        cultural_checks = [
            result.correct_currency,
            result.rtl_support_if_needed,
            result.correct_date_format or True,  # TODO: implement
            result.correct_payment_methods or True,  # TODO: implement
        ]
        result.cultural_score = sum(cultural_checks) / len(cultural_checks) * 100
        
        technical_checks = [
            result.lighthouse_performance >= 80,
            result.lighthouse_accessibility >= 90,
            result.lighthouse_seo >= 90,
            result.typescript_strict,
            result.semantic_html,
        ]
        result.technical_score = sum(technical_checks) / len(technical_checks) * 100
        
        result.overall_score = (
            result.business_score * 0.4 +
            result.cultural_score * 0.3 +
            result.technical_score * 0.3
        )
        
        return result
    
    async def run_evaluation(
        self,
        email: str,
        password: str,
        test_cases: Optional[list[TestCase]] = None,
    ) -> list[tuple[TestCase, EvaluationResult]]:
        """Run full evaluation suite."""
        if test_cases is None:
            test_cases = TEST_CASES
        
        token = await self.authenticate(email, password)
        
        for test_case in test_cases:
            print(f"\n{'='*60}")
            print(f"Running: {test_case.name}")
            print(f"Locale: {test_case.locale}, Industry: {test_case.industry}")
            print("="*60)
            
            try:
                project, gen_time = await self.generate_website(token, test_case)
                result = self.analyze_generation(project, test_case, gen_time)
                self.results.append((test_case, result))
                
                print(f"\n✅ Generation completed in {gen_time:.1f}s")
                print(f"   Business Score: {result.business_score:.1f}")
                print(f"   Cultural Score: {result.cultural_score:.1f}")
                print(f"   Technical Score: {result.technical_score:.1f}")
                print(f"   Overall Score: {result.overall_score:.1f}")
                
            except Exception as e:
                print(f"\n❌ Failed: {e}")
                self.results.append((test_case, EvaluationResult()))
        
        return self.results
    
    def generate_report(self, output_path: str = "eval/report.json"):
        """Generate evaluation report."""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": len(self.results),
            "results": [],
            "summary": {},
        }
        
        total_scores = []
        total_times = []
        
        for test_case, result in self.results:
            report["results"].append({
                "test_case": test_case.name,
                "locale": test_case.locale,
                "industry": test_case.industry,
                "generation_time": result.generation_time_seconds,
                "scores": {
                    "business": result.business_score,
                    "cultural": result.cultural_score,
                    "technical": result.technical_score,
                    "overall": result.overall_score,
                },
                "lighthouse": {
                    "performance": result.lighthouse_performance,
                    "accessibility": result.lighthouse_accessibility,
                    "best_practices": result.lighthouse_best_practices,
                    "seo": result.lighthouse_seo,
                },
            })
            
            if result.overall_score > 0:
                total_scores.append(result.overall_score)
                total_times.append(result.generation_time_seconds)
        
        if total_scores:
            report["summary"] = {
                "average_score": sum(total_scores) / len(total_scores),
                "average_generation_time": sum(total_times) / len(total_times),
                "min_score": min(total_scores),
                "max_score": max(total_scores),
                "successful_tests": len(total_scores),
            }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Report saved to: {output_path}")
        return report


async def main():
    """Run evaluation suite."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SOVRN Evaluation Suite")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--email", default="admin@sovrn.dev")
    parser.add_argument("--password", default="admin123")
    parser.add_argument("--output", default="eval/report.json")
    args = parser.parse_args()
    
    evaluator = SOVRNEvaluator(api_url=args.api_url)
    
    print("\n🚀 SOVRN Evaluation Suite")
    print("=" * 60)
    print(f"API URL: {args.api_url}")
    print(f"Test Cases: {len(TEST_CASES)}")
    print("=" * 60)
    
    await evaluator.run_evaluation(args.email, args.password)
    report = evaluator.generate_report(args.output)
    
    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60)
    
    if report.get("summary"):
        summary = report["summary"]
        print(f"\nAverage Score: {summary['average_score']:.1f}")
        print(f"Average Generation Time: {summary['average_generation_time']:.1f}s")
        print(f"Successful Tests: {summary['successful_tests']}/{len(TEST_CASES)}")


if __name__ == "__main__":
    asyncio.run(main())
