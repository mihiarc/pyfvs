"""
Species code enumeration for type-safe species handling.

This module provides a SpeciesCode enum that inherits from (str, Enum) allowing
it to be used as a string in places where species codes are expected, while
providing type safety and validation.

Usage:
    from pyfvs.species import SpeciesCode

    # Use enum directly
    species = SpeciesCode.LOBLOLLY_PINE
    print(species.value)  # "LP"

    # Convert from string
    species = SpeciesCode.from_string("LP")

    # Validate a code
    if SpeciesCode.is_valid("LP"):
        print("Valid species code")
"""

from enum import Enum
from typing import Optional


class SpeciesCode(str, Enum):
    """
    Species codes for the FVS Southern variant.

    This enum inherits from (str, Enum) so it can be used interchangeably with
    string species codes. Each enum member's value is the 2-letter FVS species code.

    Species are organized by category:
        - Southern Yellow Pines (primary species)
        - Other Pines
        - Other Softwoods
        - Oaks
        - Other Hardwoods
        - Generic/Catch-all
    """

    # =========================================================================
    # Southern Yellow Pines (Primary Species for FVS-SN)
    # =========================================================================

    LOBLOLLY_PINE = "LP"
    """Loblolly pine (Pinus taeda) - FIA code 131. Most common commercial pine in SE US."""

    SHORTLEAF_PINE = "SP"
    """Shortleaf pine (Pinus echinata) - FIA code 110. Wide-ranging southern pine."""

    LONGLEAF_PINE = "LL"
    """Longleaf pine (Pinus palustris) - FIA code 121. Fire-adapted coastal plain species."""

    SLASH_PINE = "SA"
    """Slash pine (Pinus elliottii) - FIA code 111. Fast-growing coastal species."""

    # =========================================================================
    # Other Pines
    # =========================================================================

    VIRGINIA_PINE = "VP"
    """Virginia pine (Pinus virginiana) - FIA code 132. Upland successional species."""

    POND_PINE = "PP"
    """Pond pine (Pinus serotina) - FIA code 126. Wetland pine of coastal plain."""

    SAND_PINE = "SD"
    """Sand pine (Pinus clausa) - FIA code 127. Florida scrub specialist."""

    PITCH_PINE = "PD"
    """Pitch pine (Pinus rigida) - FIA code 129. Fire-adapted Appalachian species."""

    SPRUCE_PINE = "SR"
    """Spruce pine (Pinus glabra) - FIA code 128. Shade-tolerant understory pine."""

    WHITE_PINE = "WP"
    """Eastern white pine (Pinus strobus) - FIA code 129. Large, fast-growing conifer."""

    PINE_SPECIES = "PI"
    """Generic pine species - used when exact species is unknown."""

    # =========================================================================
    # Other Softwoods
    # =========================================================================

    BALD_CYPRESS = "BY"
    """Bald cypress (Taxodium distichum) - FIA code 221. Swamp/wetland conifer."""

    POND_CYPRESS = "CO"
    """Pond cypress (Taxodium ascendens) - FIA code 222. Smaller wetland cypress."""

    EASTERN_HEMLOCK = "HM"
    """Eastern hemlock (Tsuga canadensis) - FIA code 261. Shade-tolerant Appalachian."""

    EASTERN_JUNIPER = "JU"
    """Eastern red cedar (Juniperus virginiana) - FIA code 068. Successional pioneer."""

    FRASER_FIR = "FR"
    """Fraser fir (Abies fraseri) - FIA code 012. High-elevation Appalachian endemic."""

    TAMARACK = "TM"
    """Tamarack/larch (Larix laricina) - FIA code 071. Deciduous conifer."""

    OTHER_SOFTWOOD = "OS"
    """Generic softwood species - catch-all for unlisted conifers."""

    # =========================================================================
    # Oaks (Quercus spp.)
    # =========================================================================

    WHITE_OAK = "WO"
    """White oak (Quercus alba) - FIA code 802. Premier hardwood species."""

    CHESTNUT_OAK = "CW"
    """Chestnut oak (Quercus montana) - FIA code 832. Ridge/dry site specialist."""

    SOUTHERN_RED_OAK = "SO"
    """Southern red oak (Quercus falcata) - FIA code 812. Common upland oak."""

    WATER_OAK = "WK"
    """Water oak (Quercus nigra) - FIA code 827. Bottomland/mesic species."""

    LAUREL_OAK = "LK"
    """Laurel oak (Quercus laurifolia) - FIA code 820. Semi-evergreen coastal oak."""

    OVERCUP_OAK = "OV"
    """Overcup oak (Quercus lyrata) - FIA code 822. Floodplain specialist."""

    SWAMP_OAK = "SK"
    """Swamp chestnut oak (Quercus michauxii) - FIA code 826. Bottomland species."""

    # =========================================================================
    # Maples (Acer spp.)
    # =========================================================================

    RED_MAPLE = "RM"
    """Red maple (Acer rubrum) - FIA code 316. Ubiquitous eastern hardwood."""

    SUGAR_MAPLE = "SM"
    """Sugar maple (Acer saccharum) - FIA code 318. Northern hardwood dominant."""

    SILVER_MAPLE = "SV"
    """Silver maple (Acer saccharinum) - FIA code 317. Floodplain/riparian species."""

    MAPLE_SPECIES = "MS"
    """Generic maple species - used when exact species is unknown."""

    # =========================================================================
    # Ashes (Fraxinus spp.)
    # =========================================================================

    WHITE_ASH = "WA"
    """White ash (Fraxinus americana) - FIA code 541. Upland hardwood."""

    GREEN_ASH = "GA"
    """Green ash (Fraxinus pennsylvanica) - FIA code 544. Bottomland species."""

    BLACK_ASH = "BA"
    """Black ash (Fraxinus nigra) - FIA code 543. Wetland specialist."""

    RED_ASH = "RA"
    """Red ash (Fraxinus pennsylvanica var.) - Similar to green ash."""

    # =========================================================================
    # Hickories (Carya spp.)
    # =========================================================================

    HICKORY_SPECIES = "HI"
    """Generic hickory species (Carya spp.) - FIA code 400s. Important mast producers."""

    # =========================================================================
    # Other Important Hardwoods
    # =========================================================================

    YELLOW_POPLAR = "YP"
    """Yellow-poplar/tuliptree (Liriodendron tulipifera) - FIA code 621. Fast-growing."""

    SWEETGUM = "SU"
    """Sweetgum (Liquidambar styraciflua) - FIA code 611. Common pioneer hardwood."""

    BLACK_CHERRY = "BC"
    """Black cherry (Prunus serotina) - FIA code 762. High-value timber species."""

    BLACK_GUM = "BG"
    """Black gum/tupelo (Nyssa sylvatica) - FIA code 693. Wetland edge species."""

    AMERICAN_BEECH = "BE"
    """American beech (Fagus grandifolia) - FIA code 531. Shade-tolerant climax."""

    AMERICAN_SYCAMORE = "AS"
    """American sycamore (Platanus occidentalis) - FIA code 731. Riparian giant."""

    AMERICAN_ELM = "AE"
    """American elm (Ulmus americana) - FIA code 972. Historic street tree."""

    WALNUT = "WN"
    """Black walnut (Juglans nigra) - FIA code 602. Premium timber species."""

    BASSWOOD = "BB"
    """American basswood (Tilia americana) - FIA code 951. Northern hardwood."""

    AMERICAN_BASSWOOD = "AB"
    """American basswood (Tilia americana) - Alternate code for basswood."""

    # =========================================================================
    # Minor/Understory Hardwoods
    # =========================================================================

    FLOWERING_DOGWOOD = "FM"
    """Flowering dogwood (Cornus florida) - FIA code 491. Important understory."""

    DOGWOOD = "DW"
    """Generic dogwood species."""

    AMERICAN_HORNBEAM = "AH"
    """American hornbeam (Carpinus caroliniana) - FIA code 391. Understory species."""

    HORNBEAM = "HB"
    """Generic hornbeam."""

    HOLLY = "HL"
    """American holly (Ilex opaca) - FIA code 591. Evergreen understory."""

    PERSIMMON = "PS"
    """Common persimmon (Diospyros virginiana) - FIA code 521. Wildlife mast."""

    REDBUD = "RD"
    """Eastern redbud (Cercis canadensis) - FIA code 471. Spring flowering."""

    HAWTHORN = "HA"
    """Hawthorn species (Crataegus spp.) - Small trees/shrubs."""

    CATALPA = "CT"
    """Catalpa species (Catalpa spp.) - Ornamental/naturalized."""

    BUCKEYE = "BU"
    """Buckeye species (Aesculus spp.) - FIA code 330s."""

    WILLOW = "WI"
    """Willow species (Salix spp.) - Riparian pioneers."""

    MAGNOLIA = "MG"
    """Magnolia species - Southern broadleaf evergreens."""

    # =========================================================================
    # Birches and Related
    # =========================================================================

    SWEET_BIRCH = "BD"
    """Sweet birch (Betula lenta) - FIA code 371. Appalachian species."""

    # =========================================================================
    # Tulip Tree Variants
    # =========================================================================

    TULIP_TREE = "TS"
    """Tulip tree/Yellow-poplar - Alternate code for Liriodendron tulipifera."""

    TULIP_OAK = "TO"
    """Tulip oak - Regional name variant."""

    # =========================================================================
    # Water/Swamp Species
    # =========================================================================

    WATER_TUPELO = "WT"
    """Water tupelo (Nyssa aquatica) - FIA code 694. Deep swamp species."""

    LOBLOLLY_BAY = "LB"
    """Loblolly bay (Gordonia lasianthus) - Coastal plain evergreen."""

    # =========================================================================
    # Generic/Catch-all Categories
    # =========================================================================

    OTHER_HARDWOOD = "OH"
    """Generic hardwood species - catch-all for unlisted deciduous trees."""

    OTHER_TREE = "OT"
    """Generic tree species - ultimate catch-all category."""

    @classmethod
    def from_string(cls, code: str) -> "SpeciesCode":
        """
        Convert a string species code to a SpeciesCode enum member.

        Args:
            code: A 2-letter species code string (case-insensitive)

        Returns:
            The corresponding SpeciesCode enum member

        Raises:
            ValueError: If the code is not a valid species code

        Example:
            >>> SpeciesCode.from_string("LP")
            <SpeciesCode.LOBLOLLY_PINE: 'LP'>
            >>> SpeciesCode.from_string("lp")  # Case-insensitive
            <SpeciesCode.LOBLOLLY_PINE: 'LP'>
        """
        if code is None:
            raise ValueError("Species code cannot be None")

        normalized_code = code.upper().strip()

        for member in cls:
            if member.value == normalized_code:
                return member

        valid_codes = [m.value for m in cls]
        raise ValueError(
            f"Invalid species code: '{code}'. "
            f"Valid codes include: {', '.join(sorted(valid_codes)[:10])}..."
        )

    @classmethod
    def is_valid(cls, code: str) -> bool:
        """
        Check if a string is a valid species code.

        Args:
            code: A species code string to validate

        Returns:
            True if the code is valid, False otherwise

        Example:
            >>> SpeciesCode.is_valid("LP")
            True
            >>> SpeciesCode.is_valid("XX")
            False
        """
        if code is None:
            return False

        normalized_code = code.upper().strip()

        return any(member.value == normalized_code for member in cls)

    @classmethod
    def get_pine_species(cls) -> list["SpeciesCode"]:
        """
        Get a list of all pine species codes.

        Returns:
            List of SpeciesCode enum members for pine species
        """
        return [
            cls.LOBLOLLY_PINE,
            cls.SHORTLEAF_PINE,
            cls.LONGLEAF_PINE,
            cls.SLASH_PINE,
            cls.VIRGINIA_PINE,
            cls.POND_PINE,
            cls.SAND_PINE,
            cls.PITCH_PINE,
            cls.SPRUCE_PINE,
            cls.WHITE_PINE,
            cls.PINE_SPECIES,
        ]

    @classmethod
    def get_southern_yellow_pines(cls) -> list["SpeciesCode"]:
        """
        Get the four major southern yellow pine species.

        These are the primary commercial pine species in the FVS-SN variant:
        Loblolly, Shortleaf, Longleaf, and Slash pine.

        Returns:
            List of SpeciesCode enum members for southern yellow pines
        """
        return [
            cls.LOBLOLLY_PINE,
            cls.SHORTLEAF_PINE,
            cls.LONGLEAF_PINE,
            cls.SLASH_PINE,
        ]

    @classmethod
    def get_oak_species(cls) -> list["SpeciesCode"]:
        """
        Get a list of all oak species codes.

        Returns:
            List of SpeciesCode enum members for oak species
        """
        return [
            cls.WHITE_OAK,
            cls.CHESTNUT_OAK,
            cls.SOUTHERN_RED_OAK,
            cls.WATER_OAK,
            cls.LAUREL_OAK,
            cls.OVERCUP_OAK,
            cls.SWAMP_OAK,
        ]

    @classmethod
    def list_all_codes(cls) -> list[str]:
        """
        Get a sorted list of all valid species code strings.

        Returns:
            Sorted list of 2-letter species code strings
        """
        return sorted(member.value for member in cls)

    def __str__(self) -> str:
        """Return the species code value as a string."""
        return self.value

    def __repr__(self) -> str:
        """Return a detailed string representation."""
        return f"SpeciesCode.{self.name}"


# =============================================================================
# Module-level convenience functions
# =============================================================================

def get_species_code(code: str) -> SpeciesCode:
    """
    Convert a string to a SpeciesCode enum (convenience function).

    This is an alias for SpeciesCode.from_string().

    Args:
        code: A 2-letter species code string

    Returns:
        The corresponding SpeciesCode enum member

    Raises:
        ValueError: If the code is not valid
    """
    return SpeciesCode.from_string(code)


def validate_species_code(code: str) -> bool:
    """
    Check if a species code is valid (convenience function).

    This is an alias for SpeciesCode.is_valid().

    Args:
        code: A species code string to validate

    Returns:
        True if valid, False otherwise
    """
    return SpeciesCode.is_valid(code)


# =============================================================================
# Default exports
# =============================================================================

__all__ = [
    "SpeciesCode",
    "get_species_code",
    "validate_species_code",
]
