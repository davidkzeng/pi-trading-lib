{ pkgs ? import <nixpkgs> {} }:
  pkgs.mkShell {
    nativeBuildInputs = [ 
      pkgs.which
      pkgs.python38
      pkgs.python38Packages.poetry
      pkgs.gnumake
      pkgs.cargo
      pkgs.rustc
    ];
  }
