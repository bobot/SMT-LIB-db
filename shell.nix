/* 
 * This file is a nix expression which can be used to get an isolated
 * development environemt.
 *
 * When the nix package manager is installed run 
 *  > nix-shell
 * to get a shell with the dependenies of schedgen present. This was only tested
 * on NixOS, but should work on other platforms which are supported by the Nix
 * packagemanger (such as MacOS X) too.
 */

{ pkgs ? import <nixpkgs> {} }:

pkgs.stdenv.mkDerivation {
  name = "SMT-LIB-db";

  hardeningDisable = [ "all" ];
  buildInputs = with pkgs; [
      python3
      sqlitebrowser
  ];

}
