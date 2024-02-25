/* File:    golay23.c
 * Title:   Encoder/decoder for a binary (23,12,7) Golay code
 * Author:  Robert Morelos-Zaragoza (robert@spectra.eng.hawaii.edu)
 * Date:    August 1994
 *
 * The binary (23,12,7) Golay code is an example of a perfect code, that is,
 * the number of syndromes equals the number of correctable error patterns.
 * The minimum distance is 7, so all error patterns of Hamming weight up to
 * 3 can be corrected. The total number of these error patterns is:
 *
 *       Number of errors         Number of patterns
 *       ----------------         ------------------
 *              0                         1
 *              1                        23
 *              2                       253
 *              3                      1771
 *                                     ----
 *    Total number of error patterns = 2048 = 2^{11} = number of syndromes
 *                                               --
 *                number of redundant bits -------^
 *
 * Because of its relatively low length (23), dimension (12) and number of
 * redundant bits (11), the binary (23,12,7) Golay code can be encoded and
 * decoded simply by using look-up tables. The program below uses a 16K
 * encoding table and an 8K decoding table.
 *
 * For more information, suggestions, or other ideas on implementing error
 * correcting codes, please contact me at (I'm temporarily in Japan, but
 * below is my U.S. address):
 *
 *                    Robert Morelos-Zaragoza
 *                    770 S. Post Oak Ln. #200
 *                      Houston, Texas 77056
 *
 *             email: robert@spectra.eng.hawaii.edu
 *
 *       Homework: Add an overall parity-check bit to get the (24,12,8)
 *                 extended Golay code.
 *
 * Copyright 1994 Robert Morelos-Zaragoza
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 *
 * 3. Neither the name of the copyright holder nor the names of its
 *    contributors may be used to endorse or promote products derived from this
 *    software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

/* 12-bit of data gets encoded into 23-bit of something. */

#define X22             0x00400000   /* vector representation of X^{22} */
#define X11             0x00000800   /* vector representation of X^{11} */
#define MASK12          0xfffff800   /* auxiliary vector for testing */
#define GENPOL          0x00000c75   /* generator polinomial, g(x) */

/* Global variables:
 *
 * pattern = error pattern, or information, or received vector
 * encoding_table[] = encoding table
 * decoding_table[] = decoding table
 * data = information bits, i(x)
 * codeword = code bits = x^{11}i(x) + (x^{11}i(x) mod g(x))
 * numerr = number of errors = Hamming weight of error polynomial e(x)
 * position[] = error positions in the vector representation of e(x)
 * recd = representation of corrupted received polynomial r(x) = c(x) + e(x)
 * decerror = number of decoding errors
 * a[] = auxiliary array to generate correctable error patterns
 */

long pattern;
long encoding_table[4096], decoding_table[2048];
long data, codeword, recd;
long position[23] = { 0x00000001, 0x00000002, 0x00000004, 0x00000008,
                      0x00000010, 0x00000020, 0x00000040, 0x00000080,
                      0x00000100, 0x00000200, 0x00000400, 0x00000800,
                      0x00001000, 0x00002000, 0x00004000, 0x00008000,
                      0x00010000, 0x00020000, 0x00040000, 0x00080000,
                      0x00100000, 0x00200000, 0x00400000 };
long numerr, errpos[23], decerror = 0;
int a[4];

long
arr2int(int *a, int r)
/*
 * Convert a binary vector of Hamming weight r, and nonzero positions in
 * array a[1]...a[r], to a long integer \sum_{i=1}^r 2^{a[i]-1}.
 */
{
   int i;
   long result = 0;

   for (i = 1; i <= r; i++) {
      long mul = 1;
      long temp = a[i]-1;
      while (temp--)
         mul = mul << 1;
      result += mul;
      }
   return(result);
}

void
nextcomb(int n, int r, int *a)
/*
 * Calculate next r-combination of an n-set.
 */
{
  int  i, j;

  a[r]++;
  if (a[r] <= n)
    return;

  j = r - 1;
  while (a[j] == n - r + j)
    j--;

  for (i = r; i >= j; i--)
    a[i] = a[j] + i - j + 1;

  return;
}

long
get_syndrome(long pattern)
/*
 * Compute the syndrome corresponding to the given pattern, i.e., the
 * remainder after dividing the pattern (when considering it as the vector
 * representation of a polynomial) by the generator polynomial, GENPOL.
 * In the program this pattern has several meanings: (1) pattern = infomation
 * bits, when constructing the encoding table; (2) pattern = error pattern,
 * when constructing the decoding table; and (3) pattern = received vector, to
 * obtain its syndrome in decoding.
 */
{
  if (pattern >= X11) {
    long aux = X22;
    while (pattern & MASK12) {
      while (!(aux & pattern))
	aux = aux >> 1;
      pattern ^= (aux/X11) * GENPOL;
    }
  }

  return(pattern);
}

void
init_golay(void)
{
  register int i;
  long temp;

  /*
   * ---------------------------------------------------------------------
   *                  Generate ENCODING TABLE
   *
   * An entry to the table is an information vector, a 32-bit integer,
   * whose 12 least significant positions are the information bits. The
   * resulting value is a codeword in the (23,12,7) Golay code: A 32-bit
   * integer whose 23 least significant bits are coded bits: Of these, the
   * 12 most significant bits are information bits and the 11 least
   * significant bits are redundant bits (systematic encoding).
   * ---------------------------------------------------------------------
   */
  for (pattern = 0; pattern < 4096; pattern++) {
    temp = pattern << 11;          /* multiply information by X^{11} */
    encoding_table[pattern] = temp + get_syndrome(temp);/* add redundancy */
  }

  /*
   * ---------------------------------------------------------------------
   *                  Generate DECODING TABLE
   *
   * An entry to the decoding table is a syndrome and the resulting value
   * is the most likely error pattern. First an error pattern is generated.
   * Then its syndrome is calculated and used as a pointer to the table
   * where the error pattern value is stored.
   * ---------------------------------------------------------------------
   *
   * (1) Error patterns of WEIGHT 1 (SINGLE ERRORS)
   */
  decoding_table[0] = 0;
  decoding_table[1] = 1;
  temp = 1;
  for (i = 2; i <= 23; i++) {
    temp *= 2;
    decoding_table[get_syndrome(temp)] = temp;
  }

  /*
   * (2) Error patterns of WEIGHT 2 (DOUBLE ERRORS)
   */
  a[1] = 1; a[2] = 2;
  temp = arr2int(a,2);
  decoding_table[get_syndrome(temp)] = temp;
  for (i = 1; i < 253; i++) {
    nextcomb(23,2,a);
    temp = arr2int(a,2);
    decoding_table[get_syndrome(temp)] = temp;
  }
  /*
   * (3) Error patterns of WEIGHT 3 (TRIPLE ERRORS)
   */
  a[1] = 1; a[2] = 2; a[3] = 3;
  temp = arr2int(a,3);
  decoding_table[get_syndrome(temp)] = temp;
  for (i = 1; i < 1771; i++) {
    nextcomb(23,3,a);
    temp = arr2int(a,3);
    decoding_table[get_syndrome(temp)] = temp;
  }
}
