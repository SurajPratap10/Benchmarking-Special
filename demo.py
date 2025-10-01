#!/usr/bin/env python3
"""
Demo script for the TTS Benchmarking Tool
Shows how to use the core components programmatically
"""
import asyncio
import os
from dataset import DatasetGenerator, TestSample
from benchmarking_engine import BenchmarkEngine
from tts_providers import TTSProviderFactory, TTSRequest
from export_utils import ExportManager
from text_parser import TextParser

async def run_demo():
    """Run a simple demonstration of the benchmarking tool"""
    
    print("🎙️ TTS Benchmarking Tool - Demo")
    print("=" * 50)
    
    # Check if API keys are available
    openai_key = os.getenv("OPENAI_API_KEY")
    murf_key = os.getenv("MURF_API_KEY")
    
    if not openai_key and not murf_key:
        print("❌ No API keys found. Please set OPENAI_API_KEY or MURF_API_KEY")
        print("   This demo will show the dataset generation and export features only.")
        demo_providers = []
    else:
        demo_providers = []
        if openai_key:
            demo_providers.append("openai")
        if murf_key:
            demo_providers.append("murf")
    
    # 1. Generate test dataset
    print("\n📚 Generating test dataset...")
    dataset_generator = DatasetGenerator()
    samples = dataset_generator.generate_dataset(20)  # Generate 20 samples
    
    print(f"✅ Generated {len(samples)} test samples")
    
    # Show dataset statistics
    stats = dataset_generator.get_dataset_stats()
    print(f"   Categories: {list(stats['categories'].keys())}")
    print(f"   Word count range: {stats['word_count_stats']['min']}-{stats['word_count_stats']['max']}")
    print(f"   Average complexity: {stats['complexity_stats']['avg']:.2f}")
    
    # 2. Show sample texts
    print("\n📝 Sample texts:")
    for i, sample in enumerate(samples[:3]):
        print(f"   {i+1}. [{sample.category}] {sample.text[:60]}...")
    
    # 3. Initialize benchmarking engine
    print("\n🔧 Initializing benchmarking engine...")
    benchmark_engine = BenchmarkEngine()
    
    if demo_providers:
        # 4. Run a small benchmark
        print(f"\n🚀 Running benchmark with providers: {demo_providers}")
        
        # Use first 3 samples for demo
        demo_samples = samples[:3]
        
        # Configure voices
        voices_per_provider = {}
        for provider_id in demo_providers:
            try:
                provider = TTSProviderFactory.create_provider(provider_id)
                voices = provider.get_available_voices()
                voices_per_provider[provider_id] = [voices[0]]  # Use first voice only
                print(f"   {provider_id}: using voice '{voices[0]}'")
            except Exception as e:
                print(f"   ❌ Failed to initialize {provider_id}: {e}")
                demo_providers.remove(provider_id)
        
        if demo_providers:
            # Run benchmark
            results = await benchmark_engine.run_benchmark_suite(
                providers=demo_providers,
                samples=demo_samples,
                voices_per_provider=voices_per_provider,
                iterations=1  # Single iteration for demo
            )
            
            print(f"✅ Completed {len(results)} tests")
            
            # 5. Show results summary
            print("\n📊 Results Summary:")
            summaries = benchmark_engine.calculate_summary_stats(results)
            
            for provider, summary in summaries.items():
                print(f"   {provider.title()}:")
                print(f"     Success Rate: {summary.success_rate:.1f}%")
                print(f"     Avg Latency: {summary.avg_latency_ms:.1f}ms")
                print(f"     Total Tests: {summary.total_tests}")
            
            # 6. Update ELO ratings
            benchmark_engine.update_elo_ratings(results)
            leaderboard = benchmark_engine.get_leaderboard()
            
            print("\n🏆 ELO Leaderboard:")
            for entry in leaderboard:
                print(f"   {entry['rank']}. {entry['provider'].title()}: {entry['elo_rating']:.1f}")
            
            # 7. Export results
            print("\n📤 Exporting results...")
            export_manager = ExportManager()
            
            # Export as JSON
            json_file = export_manager.export_results_json(results)
            print(f"   ✅ JSON export: {json_file}")
            
            # Export as CSV
            csv_file = export_manager.export_results_csv(results)
            print(f"   ✅ CSV export: {csv_file}")
            
            # Create comprehensive report
            report_file = export_manager.export_summary_report(results, summaries, leaderboard)
            print(f"   ✅ Report export: {report_file}")
            
        else:
            print("❌ No providers available for testing")
    
    else:
        print("⚠️  Skipping benchmark tests (no API keys available)")
    
    # 8. Demonstrate text parser functionality
    print("\n📁 Demonstrating text parser...")
    text_parser = TextParser()
    
    # Create a sample text file content
    sample_text_content = """
    This is a sample text file for demonstration.
    It contains multiple lines of text that can be used for TTS benchmarking.
    
    The text parser can extract meaningful sentences from various file formats.
    Each line becomes a potential test sample for the benchmarking system.
    
    This demonstrates how users can upload their own content for testing.
    """
    
    # Parse the sample content
    parsed_texts = text_parser.parse_uploaded_file(sample_text_content, "demo.txt")
    print(f"   ✅ Parsed {len(parsed_texts)} text segments")
    
    # Convert to test samples
    custom_samples = text_parser.create_test_samples_from_parsed(parsed_texts, auto_categorize=True)
    print(f"   ✅ Created {len(custom_samples)} test samples from parsed text")
    
    # Show sample details
    if custom_samples:
        print("   📋 Sample details:")
        for sample in custom_samples[:2]:
            print(f"      - {sample.category}: {sample.text[:50]}...")
    
    # 9. Export dataset
    print("\n💾 Exporting dataset...")
    dataset_file = "demo_dataset.json"
    dataset_generator.export_dataset(dataset_file)
    print(f"   ✅ Dataset exported: {dataset_file}")
    
    # Export custom samples
    if custom_samples:
        custom_dataset_file = "demo_custom_dataset.json"
        # Temporarily set custom samples for export
        original_samples = dataset_generator.samples
        dataset_generator.samples = custom_samples
        dataset_generator.export_dataset(custom_dataset_file)
        dataset_generator.samples = original_samples
        print(f"   ✅ Custom samples exported: {custom_dataset_file}")
    
    print("\n🎉 Demo completed!")
    print("\nFeatures demonstrated:")
    print("   ✅ Dataset generation")
    print("   ✅ Text file parsing")
    print("   ✅ Custom sample creation")
    print("   ✅ Export functionality")
    if demo_providers:
        print("   ✅ TTS benchmarking")
        print("   ✅ ELO rating system")
    
    print("\nTo run the full interactive application:")
    print("   python run.py")
    print("   or")
    print("   streamlit run app.py")
    
    print("\nNew Upload Feature:")
    print("   📁 Upload custom text files (TXT, CSV, JSON, MD, PY, JS, HTML)")
    print("   ✍️  Manual text input")
    print("   🔄 Auto-categorization of content")
    print("   📊 Integration with batch benchmarking")

def main():
    """Main demo function"""
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")

if __name__ == "__main__":
    main()
