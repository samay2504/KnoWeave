"""
Perception Agent - Text analysis and metadata extraction
Extracts surface features: tokens, POS, NER, coref, SRL, tone, POV, summaries
"""

import re
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# Use production-ready import system
try:
    from core.imports import import_manager, optional_import
    PRODUCTION_IMPORTS = True
except ImportError:
    # Fallback during transition
    PRODUCTION_IMPORTS = False

if PRODUCTION_IMPORTS:
    # Use production import system
    from utils.schemas import PerceptionOutput, WorkspaceSchema
    from utils.logging_cfg import get_agent_logger
    
    # Dynamic imports with fallbacks
    spacy = import_manager.safe_import('spacy')
    English = import_manager.get_attribute('spacy.lang.en', 'English')
    SPACY_AVAILABLE = spacy is not None
    
    stanza = import_manager.safe_import('stanza')
    STANZA_AVAILABLE = stanza is not None
    
    nltk = import_manager.safe_import('nltk')
    word_tokenize = import_manager.get_attribute('nltk.tokenize', 'word_tokenize')
    sent_tokenize = import_manager.get_attribute('nltk.tokenize', 'sent_tokenize')
    pos_tag = import_manager.get_attribute('nltk.tag', 'pos_tag')
    NLTK_AVAILABLE = nltk is not None
    
else:
    # Fallback import system
    from utils.schemas import PerceptionOutput, WorkspaceSchema
    from utils.logging_cfg import get_agent_logger

    # Try to import spaCy for advanced NLP
    try:
        import spacy
        from spacy.lang.en import English
        SPACY_AVAILABLE = True
    except ImportError:
        SPACY_AVAILABLE = False

    # Try to import stanza as fallback
    try:
        import stanza
        STANZA_AVAILABLE = True
    except ImportError:
        STANZA_AVAILABLE = False

    # Try to import NLTK for basic processing
    try:
        import nltk
        from nltk.tokenize import word_tokenize, sent_tokenize
        from nltk.tag import pos_tag
        NLTK_AVAILABLE = True
    except ImportError:
        NLTK_AVAILABLE = False

logger = get_agent_logger("perception")


@dataclass
class Entity:
    """Named entity representation"""

    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class Token:
    """Token representation with linguistic features"""

    text: str
    pos: str
    lemma: str
    start: int
    end: int
    is_alpha: bool = False
    is_stop: bool = False


class PerceptionAgent:
    """Agent for text analysis and feature extraction"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.nlp_model = None
        self.nlp_type = None
        self.initialized = False

        # Pattern-based fallbacks
        self.sentence_pattern = re.compile(r"[.!?]+\s+")
        self.word_pattern = re.compile(r"\b\w+\b")
        self.entity_patterns = {
            "PERSON": re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"),
            "LOCATION": re.compile(
                r"\b(?:in|at|from|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
            ),
            "TIME": re.compile(
                r"\b(?:today|yesterday|tomorrow|morning|evening|night|day|week|month|year)\b",
                re.IGNORECASE,
            ),
        }

        # POV patterns
        self.first_person_patterns = re.compile(
            r"\b(I|me|my|mine|myself|we|us|our|ours|ourselves)\b", re.IGNORECASE
        )
        self.second_person_patterns = re.compile(
            r"\b(you|your|yours|yourself|yourselves)\b", re.IGNORECASE
        )
        self.third_person_patterns = re.compile(
            r"\b(he|him|his|himself|she|her|hers|herself|it|its|itself|they|them|their|theirs|themselves)\b",
            re.IGNORECASE,
        )

        # Tone indicators
        self.positive_words = {
            "happy",
            "joy",
            "excited",
            "wonderful",
            "amazing",
            "great",
            "fantastic",
            "love",
            "beautiful",
            "brilliant",
            "excellent",
            "perfect",
            "awesome",
        }
        self.negative_words = {
            "sad",
            "angry",
            "terrible",
            "awful",
            "hate",
            "horrible",
            "disgusting",
            "furious",
            "devastated",
            "miserable",
            "depressed",
            "anxious",
            "worried",
        }
        self.question_words = {"what", "who", "where", "when", "why", "how", "which"}

    async def initialize(self) -> bool:
        """Initialize the NLP model asynchronously"""
        if self.initialized:
            return True

        try:
            # Try spaCy first
            if SPACY_AVAILABLE:
                await self._initialize_spacy()
            # Then try stanza
            elif STANZA_AVAILABLE:
                await self._initialize_stanza()
            # Fall back to NLTK
            elif NLTK_AVAILABLE:
                await self._initialize_nltk()
            else:
                logger.warning("No NLP library available, using pattern-based fallback")
                self.nlp_type = "pattern"

            self.initialized = True
            logger.info(f"Perception agent initialized with {self.nlp_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize perception agent: {e}")
            self.nlp_type = "pattern"
            self.initialized = True
            return False

    async def _initialize_spacy(self) -> None:
        """Initialize spaCy model with production-ready import handling"""
        try:
            # Try to load the model in a thread to avoid blocking
            loop = asyncio.get_event_loop()

            def load_model():
                if not SPACY_AVAILABLE:
                    raise ImportError("spaCy not available")
                
                try:
                    # Try small English model first
                    return spacy.load("en_core_web_sm")
                except OSError:
                    try:
                        # Try medium model
                        return spacy.load("en_core_web_md")
                    except OSError:
                        # Create blank model as fallback
                        if PRODUCTION_IMPORTS and English:
                            nlp = English()
                        else:
                            # Fallback using dynamic import
                            english_cls = import_manager.get_attribute('spacy.lang.en', 'English') if PRODUCTION_IMPORTS else English
                            nlp = english_cls()
                        nlp.add_pipe("sentencizer")
                        return nlp

            self.nlp_model = await loop.run_in_executor(None, load_model)
            self.nlp_type = "spacy"

        except Exception as e:
            logger.warning(f"spaCy initialization failed: {e}")
            raise

    async def _initialize_stanza(self) -> None:
        """Initialize stanza model with production-ready import handling"""
        try:
            if not STANZA_AVAILABLE:
                raise ImportError("Stanza not available")
                
            loop = asyncio.get_event_loop()

            def load_stanza():
                # Download model if not present
                stanza.download("en", verbose=False)
                return stanza.Pipeline(
                    "en", processors="tokenize,pos,lemma,ner", verbose=False
                )

            self.nlp_model = await loop.run_in_executor(None, load_stanza)
            self.nlp_type = "stanza"

        except Exception as e:
            logger.warning(f"Stanza initialization failed: {e}")
            raise

    async def _initialize_nltk(self) -> None:
        """Initialize NLTK components with production-ready import handling"""
        try:
            if not NLTK_AVAILABLE:
                raise ImportError("NLTK not available")
                
            loop = asyncio.get_event_loop()

            def download_nltk_data():
                try:
                    nltk.download("punkt", quiet=True)
                    nltk.download("averaged_perceptron_tagger", quiet=True)
                    nltk.download("stopwords", quiet=True)
                    return True
                except Exception:
                    return False

            await loop.run_in_executor(None, download_nltk_data)
            self.nlp_type = "nltk"

        except Exception as e:
            logger.warning(f"NLTK initialization failed: {e}")
            raise

    async def cleanup(self):
        """Cleanup perception agent resources"""
        logger.info("Cleaning up Perception Agent")
        self.nlp_model = None
        self.initialized = False
        logger.info("Perception Agent cleanup completed")

    async def invoke(
        self, workspace: Dict[str, Any], agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Blueprint-compliant invoke method for Perception Agent
        Analyzes text and extracts surface features as per blueprint specification
        """
        if not self.initialized:
            await self.initialize()

        # Extract text from workspace (blueprint format)
        text = workspace.get("topic_content", "")
        if not text.strip():
            return self._empty_analysis()

        try:
            # Extract features based on available NLP library
            if self.nlp_type == "spacy":
                result = await self._analyze_with_spacy(text)
            elif self.nlp_type == "stanza":
                result = await self._analyze_with_stanza(text)
            elif self.nlp_type == "nltk":
                result = await self._analyze_with_nltk(text)
            else:
                result = await self._analyze_with_patterns(text)

            # Convert PerceptionOutput to blueprint format
            return self._convert_to_blueprint_format(result, text)

        except Exception as e:
            logger.error(f"Text analysis failed: {e}")
            # Fallback to pattern-based analysis
            result = await self._analyze_with_patterns(text)
            return self._convert_to_blueprint_format(result, text)

    def _convert_to_blueprint_format(
        self, perception_output: PerceptionOutput, text: str
    ) -> Dict[str, Any]:
        """Convert PerceptionOutput to blueprint-specified format"""
        # Extract character information from entities
        characters = []
        for entity in perception_output.entities:
            if entity.get("label") in ["PERSON", "PER"]:
                characters.append(
                    {
                        "name": entity["text"],
                        "traits": [],  # Could be enhanced with trait extraction
                        "mentions": text.lower().count(entity["text"].lower()),
                        "confidence": entity.get("confidence", 0.8),
                    }
                )

        # Extract events (simple approach - sentences with action verbs)
        events = self._extract_events_from_text(text)

        return {
            "tokens": perception_output.tokens,
            "entities": perception_output.entities,
            "characters": characters,
            "events": events,
            "pov": perception_output.pov or "unknown",
            "tense": "unknown",  # Could be enhanced
            "tone": perception_output.tone or "neutral",
            "summary": perception_output.summary,
            "flags": {
                "low_confidence_entities": [
                    entity["text"]
                    for entity in perception_output.entities
                    if entity.get("confidence", 1.0) < 0.7
                ]
            },
            "metadata": perception_output.metadata,
        }

    def _extract_events_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract events from text for blueprint format"""
        events = []
        sentences = re.split(r"[.!?]+", text)

        action_verbs = {
            "walked",
            "ran",
            "said",
            "told",
            "found",
            "discovered",
            "opened",
            "closed",
            "entered",
            "left",
            "saw",
            "heard",
            "felt",
            "thought",
            "decided",
            "realized",
            "went",
            "came",
            "moved",
            "jumped",
            "looked",
        }

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            words = set(word.lower() for word in re.findall(r"\b\w+\b", sentence))
            if words.intersection(action_verbs):
                events.append(
                    {
                        "summary": (
                            sentence[:100] + "..." if len(sentence) > 100 else sentence
                        ),
                        "actors": [],  # Could be enhanced with entity extraction
                        "confidence": 0.6,
                        "sentence_index": i,
                    }
                )

        return events[:10]  # Limit to top 10 events

    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis structure for blueprint compliance"""
        return {
            "tokens": [],
            "entities": [],
            "characters": [],
            "events": [],
            "pov": "unknown",
            "tense": "unknown",
            "tone": "neutral",
            "summary": "",
            "flags": {"low_confidence_entities": []},
            "metadata": {"analysis_type": "empty"},
        }

    async def _analyze_with_spacy(self, text: str) -> PerceptionOutput:
        """Analyze text using spaCy"""
        loop = asyncio.get_event_loop()

        def process_text():
            doc = self.nlp_model(text)

            # Extract tokens
            tokens = [token.text for token in doc if not token.is_space]
            pos_tags = [token.pos_ for token in doc if not token.is_space]

            # Extract entities
            entities = [
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "confidence": 1.0,
                }
                for ent in doc.ents
            ]

            # Extract sentences for summary
            sentences = [sent.text.strip() for sent in doc.sents]

            return tokens, pos_tags, entities, sentences

        tokens, pos_tags, entities, sentences = await loop.run_in_executor(
            None, process_text
        )

        # Analyze tone and POV
        tone = self._detect_tone(text)
        pov = self._detect_pov(text)

        # Generate summary
        summary = self._generate_summary(sentences)

        return PerceptionOutput(
            tokens=tokens[:100],  # Limit to first 100 tokens
            pos_tags=pos_tags[:100],
            entities=entities,
            tone=tone,
            pov=pov,
            summary=summary,
            metadata={
                "sentence_count": len(sentences),
                "word_count": len(tokens),
                "entity_count": len(entities),
                "analysis_type": "spacy",
            },
        )

    async def _analyze_with_stanza(self, text: str) -> PerceptionOutput:
        """Analyze text using Stanza"""
        loop = asyncio.get_event_loop()

        def process_text():
            doc = self.nlp_model(text)

            tokens = []
            pos_tags = []
            entities = []

            for sentence in doc.sentences:
                for token in sentence.tokens:
                    for word in token.words:
                        tokens.append(word.text)
                        pos_tags.append(word.pos)

                # Extract entities
                for ent in sentence.ents:
                    entities.append(
                        {
                            "text": ent.text,
                            "label": ent.type,
                            "start": ent.start_char,
                            "end": ent.end_char,
                            "confidence": 1.0,
                        }
                    )

            sentences = [sent.text for sent in doc.sentences]
            return tokens, pos_tags, entities, sentences

        tokens, pos_tags, entities, sentences = await loop.run_in_executor(
            None, process_text
        )

        tone = self._detect_tone(text)
        pov = self._detect_pov(text)
        summary = self._generate_summary(sentences)

        return PerceptionOutput(
            tokens=tokens[:100],
            pos_tags=pos_tags[:100],
            entities=entities,
            tone=tone,
            pov=pov,
            summary=summary,
            metadata={
                "sentence_count": len(sentences),
                "word_count": len(tokens),
                "entity_count": len(entities),
                "analysis_type": "stanza",
            },
        )

    async def _analyze_with_nltk(self, text: str) -> PerceptionOutput:
        """Analyze text using NLTK"""
        loop = asyncio.get_event_loop()

        def process_text():
            # Tokenization
            sentences = sent_tokenize(text)
            tokens = word_tokenize(text)

            # POS tagging
            pos_tags = [tag for word, tag in pos_tag(tokens)]

            # Simple NER using patterns
            entities = self._extract_entities_with_patterns(text)

            return tokens, pos_tags, entities, sentences

        tokens, pos_tags, entities, sentences = await loop.run_in_executor(
            None, process_text
        )

        tone = self._detect_tone(text)
        pov = self._detect_pov(text)
        summary = self._generate_summary(sentences)

        return PerceptionOutput(
            tokens=tokens[:100],
            pos_tags=pos_tags[:100],
            entities=entities,
            tone=tone,
            pov=pov,
            summary=summary,
            metadata={
                "sentence_count": len(sentences),
                "word_count": len(tokens),
                "entity_count": len(entities),
                "analysis_type": "nltk",
            },
        )

    async def _analyze_with_patterns(self, text: str) -> PerceptionOutput:
        """Analyze text using pattern-based approach"""
        # Simple tokenization
        sentences = self.sentence_pattern.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        tokens = self.word_pattern.findall(text)

        # Simple POS tagging (very basic)
        pos_tags = ["NOUN" if token[0].isupper() else "WORD" for token in tokens]

        # Pattern-based entity extraction
        entities = self._extract_entities_with_patterns(text)

        tone = self._detect_tone(text)
        pov = self._detect_pov(text)
        summary = self._generate_summary(sentences)

        return PerceptionOutput(
            tokens=tokens[:100],
            pos_tags=pos_tags[:100],
            entities=entities,
            tone=tone,
            pov=pov,
            summary=summary,
            metadata={
                "sentence_count": len(sentences),
                "word_count": len(tokens),
                "entity_count": len(entities),
                "analysis_type": "pattern",
            },
        )

    def _extract_entities_with_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities using regex patterns"""
        entities = []

        for entity_type, pattern in self.entity_patterns.items():
            for match in pattern.finditer(text):
                entities.append(
                    {
                        "text": match.group().strip(),
                        "label": entity_type,
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.7,  # Lower confidence for pattern-based
                    }
                )

        return entities

    def _detect_tone(self, text: str) -> Optional[str]:
        """Detect overall tone of the text"""
        words = set(word.lower() for word in self.word_pattern.findall(text))

        positive_score = len(words.intersection(self.positive_words))
        negative_score = len(words.intersection(self.negative_words))

        # Check for questions
        question_score = sum(1 for word in words if word in self.question_words)
        if text.count("?") > 0 or question_score > 0:
            return "questioning"

        if positive_score > negative_score:
            return "positive" if positive_score > 2 else "neutral"
        elif negative_score > positive_score:
            return "negative" if negative_score > 2 else "neutral"
        else:
            return "neutral"

    def _detect_pov(self, text: str) -> Optional[str]:
        """Detect point of view (first, second, third person)"""
        first_person_count = len(self.first_person_patterns.findall(text))
        second_person_count = len(self.second_person_patterns.findall(text))
        third_person_count = len(self.third_person_patterns.findall(text))

        total_pronouns = first_person_count + second_person_count + third_person_count

        if total_pronouns == 0:
            return None

        # Determine dominant POV
        if (
            first_person_count > second_person_count
            and first_person_count > third_person_count
        ):
            return "first"
        elif (
            second_person_count > first_person_count
            and second_person_count > third_person_count
        ):
            return "second"
        elif (
            third_person_count > first_person_count
            and third_person_count > second_person_count
        ):
            return "third"
        else:
            return "mixed"

    def _generate_summary(self, sentences: List[str]) -> str:
        """Generate a simple summary of the text"""
        if not sentences:
            return ""

        # Simple extractive summarization - take first and key sentences
        summary_sentences = []

        # Always include first sentence if it exists
        if sentences:
            summary_sentences.append(sentences[0])

        # Add sentences with important indicators
        important_indicators = {
            "however",
            "therefore",
            "finally",
            "importantly",
            "because",
            "since",
        }

        for sentence in sentences[1:]:
            words = set(word.lower() for word in self.word_pattern.findall(sentence))
            if words.intersection(important_indicators):
                summary_sentences.append(sentence)
                if len(summary_sentences) >= 3:  # Limit to 3 sentences
                    break

        # If we don't have enough, add the last sentence
        if len(summary_sentences) < 2 and len(sentences) > 1:
            summary_sentences.append(sentences[-1])

        return " ".join(summary_sentences)[:500]  # Limit to 500 characters


async def create_perception_agent(config: Dict[str, Any]) -> PerceptionAgent:
    """Factory function to create perception agent"""
    agent = PerceptionAgent(config)
    await agent.initialize()
    return agent
