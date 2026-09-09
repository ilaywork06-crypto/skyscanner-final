/**
 * The vocabulary of the table, in both languages.
 *
 * What is here is what this library itself draws: the filter chips above a table, the bar below it, the
 * viewers a cell opens, the dropzone a file is picked in. The words a product uses for its own subject -
 * whether a row is an event or an assumption - belong to that product and are registered by it, over the
 * top of these, through the very same `registerTranslations`.
 *
 * Two rules the Hebrew is written by, both of them the sort of thing that reads as broken translation
 * rather than as a bug:
 *
 *   - Hebrew has no capitals, so a phrase that carries meaning through case in English - CLEAR ALL FILTERS
 *     shouting because it is an action - has to carry it some other way, and here that is simply plain
 *     words. Uppercasing Hebrew with CSS produces nothing at all, which is worse than not shouting.
 *   - A number written into a right to left sentence is still read left to right, and a range written as
 *     `1 – 25` keeps its own direction in the middle of Hebrew words. The ranges are therefore phrased so
 *     that the numbers sit at the edges of the sentence rather than in the middle of it, where the
 *     browser's own bidirectional algorithm would otherwise have to guess which side the dash belongs to.
 */

import { registerTranslations, type Translations } from '../composables/useLanguage'

/** The phrases this library draws with, which every product gets whether it registers anything or not. */
const SHARED_TRANSLATIONS: Translations = {
  en: {
    /* The chips above a table naming what currently narrows it. */
    'filters.activeLabel': 'Filtered by',
    'filters.clearAll': 'CLEAR ALL FILTERS',
    'filters.remove': 'Remove the filter {label}',
    'filters.search': 'Search',
    'filters.searchIn': 'Search {field}',
    'filters.clear': 'Clear',
    'filters.selectAll': 'Select all',
    'filters.noMatch': 'No value matches "{term}".',
    'filters.values': 'values',
    'quick.label': 'Quick filters',
    'quick.clear': 'CLEAR QUICK FILTERS',
    'quick.picked': '{count} picked',

    /* How a condition of a column filter reads once it is written out as a sentence. */
    'operator.equals': 'is',
    'operator.not_equals': 'is not',
    'operator.contains': 'contains',
    'operator.not_contains': 'does not contain',
    'operator.starts_with': 'starts with',
    'operator.ends_with': 'ends with',
    'operator.greater_than': 'is above',
    'operator.greater_or_equal': 'is at least',
    'operator.less_than': 'is below',
    'operator.less_or_equal': 'is at most',
    'operator.in': 'is one of',
    'operator.not_in': 'is none of',
    'operator.between': 'is between',
    'operator.is_empty': 'is empty',
    'operator.is_not_empty': 'is filled',

    /* The bar below a table. A product renames the rows it counts by registering these again. */
    'pagination.empty': 'No rows',
    'pagination.range': '{first} – {last} of {total} rows',

    /* The chevron that opens the panel underneath a row. */
    'row.expand': 'Show the details of this row',
    'row.collapse': 'Hide the details of this row',

    /* The panel of attributes a row opens, and the viewers one of its values opens. */
    'attributes.empty': 'Nothing was recorded here yet.',
    'attributes.notDeclared': 'not declared',
    'value.title': 'Value',
    'value.copy': 'Copy the value',
    'value.copied': 'Copied',
    'value.close': 'Close',
    'value.coordinate': 'Coordinate',
    'value.more': 'More information',

    /* Picking files, and the list they end up in. */
    'files.label': 'Files',
    'files.dropzone': 'Drag & Drop Or Click',
    'files.dropzoneHint': 'Multiple files are allowed, but the same file name only once',
    'files.remove': 'Remove {name}',
    'files.empty': 'No files',
    'files.download': 'Download',
    'files.open': 'Open',

    /* The inputs a dynamic field is filled in through. */
    'input.notesPlaceholder': 'Type here...',
    'input.latitude': 'Latitude',
    'input.longitude': 'Longitude',
    'input.altitude': 'Altitude (m)',
    'input.clearCoordinate': 'Clear the coordinate',
    'input.enterToAdd':
      'Type a value and press Enter to add it. Each value becomes its own chip, and anything still being ' +
      'typed when the form is saved is not kept.',
    'input.note': 'Note {number}',
    'input.addNote': 'ADD NOTE',
    'files.openNamed': 'Open {name}',

    /* The two answers a boolean cell has, and the placeholder a cell with nothing in it draws. */
    'common.yes': 'Yes',
    'common.no': 'No',
    'common.cancel': 'Cancel',
    'common.save': 'Save',
    'common.close': 'Close',
    'common.discard': 'Discard',
    'common.keepEditing': 'Keep editing',
    'common.unsavedTitle': 'Leave without saving?',
    'common.unsavedBody': 'The changes made here have not been saved and will be lost.',

    /* The language switch itself, which has to be readable in the language being left as well as the one taken. */
    'language.label': 'Language',
    'language.english': 'English',
    'language.hebrew': 'עברית',

    /* AG Grid's own words, handed to it as its locale text. */
    'grid.noRowsToShow': 'No rows to show',
    'grid.loading': 'Loading…',
    'grid.pinColumn': 'Pin column',
    'grid.pinLeft': 'Pin left',
    'grid.pinRight': 'Pin right',
    'grid.noPin': 'No pin',
    'grid.autosizeThisColumn': 'Autosize this column',
    'grid.autosizeAllColumns': 'Autosize all columns',
    'grid.resetColumns': 'Reset columns',
    'grid.sortAscending': 'Sort ascending',
    'grid.sortDescending': 'Sort descending',
    'grid.sortUnSort': 'Clear sort',
    'grid.chooseColumns': 'Choose columns',
    'grid.columns': 'Columns',
  },
  he: {
    'filters.activeLabel': 'מסונן לפי',
    'filters.clearAll': 'ניקוי כל הסינונים',
    'filters.remove': 'הסרת הסינון {label}',
    'filters.search': 'חיפוש',
    'filters.searchIn': 'חיפוש בעמודה {field}',
    'filters.clear': 'ניקוי',
    'filters.selectAll': 'בחירת הכול',
    'filters.noMatch': 'אין ערך שמתאים ל"{term}".',
    'filters.values': 'ערכים',
    'quick.label': 'סינון מהיר',
    'quick.clear': 'ניקוי הסינון המהיר',
    'quick.picked': 'נבחרו {count}',

    'operator.equals': 'שווה ל',
    'operator.not_equals': 'שונה מ',
    'operator.contains': 'מכיל',
    'operator.not_contains': 'אינו מכיל',
    'operator.starts_with': 'מתחיל ב',
    'operator.ends_with': 'מסתיים ב',
    'operator.greater_than': 'גדול מ',
    'operator.greater_or_equal': 'לכל הפחות',
    'operator.less_than': 'קטן מ',
    'operator.less_or_equal': 'לכל היותר',
    'operator.in': 'אחד מתוך',
    'operator.not_in': 'אף אחד מתוך',
    'operator.between': 'בין',
    'operator.is_empty': 'ריק',
    'operator.is_not_empty': 'מלא',

    /* The count leads the sentence rather than sitting inside it, so the digits keep their own direction. */
    'pagination.empty': 'אין שורות',
    'pagination.range': 'מתוך {total} שורות מוצגות {first} עד {last}',

    'row.expand': 'הצגת פרטי השורה',
    'row.collapse': 'הסתרת פרטי השורה',

    'attributes.empty': 'עדיין לא נרשם כאן דבר.',
    'attributes.notDeclared': 'לא הוגדר',
    'value.title': 'ערך',
    'value.copy': 'העתקת הערך',
    'value.copied': 'הועתק',
    'value.close': 'סגירה',
    'value.coordinate': 'נקודת ציון',
    'value.more': 'מידע נוסף',

    'files.label': 'קבצים',
    'files.dropzone': 'גררו לכאן קובץ או לחצו לבחירה',
    'files.dropzoneHint': 'אפשר לבחור כמה קבצים, אבל כל שם קובץ פעם אחת בלבד',
    'files.remove': 'הסרת {name}',
    'files.empty': 'אין קבצים',
    'files.download': 'הורדה',
    'files.open': 'פתיחה',

    'input.notesPlaceholder': 'הקלידו כאן...',
    'input.latitude': 'קו רוחב',
    'input.longitude': 'קו אורך',
    'input.altitude': 'גובה (מ׳)',
    'input.clearCoordinate': 'ניקוי נקודת הציון',
    'input.enterToAdd':
      'הקלידו ערך ולחצו Enter כדי להוסיף אותו. כל ערך הופך לתגית משלו, וערך שנשאר בהקלדה בזמן השמירה ' +
      'אינו נשמר.',
    'input.note': 'הערה {number}',
    'input.addNote': 'הוספת הערה',
    'files.openNamed': 'פתיחת {name}',

    'common.yes': 'כן',
    'common.no': 'לא',
    'common.cancel': 'ביטול',
    'common.save': 'שמירה',
    'common.close': 'סגירה',
    'common.discard': 'ביטול השינויים',
    'common.keepEditing': 'המשך עריכה',
    'common.unsavedTitle': 'לצאת בלי לשמור?',
    'common.unsavedBody': 'השינויים שנעשו כאן לא נשמרו והם יאבדו.',

    'language.label': 'שפה',
    'language.english': 'English',
    'language.hebrew': 'עברית',

    'grid.noRowsToShow': 'אין שורות להצגה',
    'grid.loading': 'טוען…',
    'grid.pinColumn': 'נעיצת עמודה',
    'grid.pinLeft': 'נעיצה לימין',
    'grid.pinRight': 'נעיצה לשמאל',
    'grid.noPin': 'ללא נעיצה',
    'grid.autosizeThisColumn': 'התאמת רוחב העמודה',
    'grid.autosizeAllColumns': 'התאמת רוחב כל העמודות',
    'grid.resetColumns': 'איפוס העמודות',
    'grid.sortAscending': 'מיון עולה',
    'grid.sortDescending': 'מיון יורד',
    'grid.sortUnSort': 'ביטול המיון',
    'grid.chooseColumns': 'בחירת עמודות',
    'grid.columns': 'עמודות',
  },
}

/*
 * Registered as this module is loaded rather than by whoever imports it, so that a component of this library
 * has its words the moment it renders. A product that registers nothing still gets a working table, and a
 * product that registers its own does so afterwards and therefore wins wherever the two name the same key.
 */
registerTranslations(SHARED_TRANSLATIONS)

export { SHARED_TRANSLATIONS }
